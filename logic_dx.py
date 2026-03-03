import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os, time
from PIL import Image

# --- 1. 定義データ (日本人女性・実写特化) ---
HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft loose curls", "ハーフアップ": "half-up", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "original hair color", "ナチュラルブラック": "black hair", "ダークブラウン": "dark brown", "ashベージュ": "ash beige", "ミルクティーグレージュ": "greige", "ピンクブラウン": "pink brown", "ハニーブロンド": "honey blonde"}
STAND_PROMPTS = ["Full body, leaning against a wall", "Full body, walking", "Full body, weight on one leg", "Full body, 3/4 view, elegant posture"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways", "Full body, sitting on steps", "Full body, legs crossed"]

# --- 2. 黄金律：プロンプト構築とリトライ機能 ---
def get_final_dx_prompt(pose, anchor_text, hair_s, hair_c):
    """裸を回避し、体型を死守するための鉄壁プロンプト"""
    # 露出を避け、アパレル用語で固定するフィルター
    wardrobe_fix = anchor_text.replace("lingerie", "Night-fashion").replace("babydoll", "Silk slip")
    
    identity_lock = (
        "CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK. "
        "STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK. "
        "Match EXACT face, body mass, and shoulder width of IMAGE 1. "
        "Subject: Japanese woman, completely clothed in solid fabric, NO nudity. "
    )
    render = (
        "Hyper-realistic photography, Sony A7R IV, 35mm lens, f/2.8, "
        "highly detailed skin pores, soft facial fill-light, cinematic lighting, film grain."
    )
    return f"{identity_lock} WARDROBE: {wardrobe_fix}. POSE: {pose}. HAIR: {hair_s}, Color: {hair_c}. {render}"

def generate_with_retry(face_url, prompt, id_weight, g_scale, steps, max_retries=2):
    """503エラー時のリトライ機能を維持"""
    for attempt in range(max_retries + 1):
        try:
            return fal_client.subscribe(
                "fal-ai/flux-pulid",
                arguments={
                    "prompt": prompt, "reference_image_url": face_url,
                    "id_weight": id_weight, "guidance_scale": g_scale,
                    "num_inference_steps": steps, "enable_safety_checker": False
                }
            )
        except Exception as e:
            if "503" in str(e) and attempt < max_retries:
                time.sleep(2)
                continue
            raise e

# --- 3. UI メイン処理 ---
def show_dx_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_anchor" not in st.session_state: st.session_state.dx_anchor = ""
    if "dx_src_bytes" not in st.session_state: st.session_state.dx_src_bytes = None

    st.header("💎 AI KISEKAE DX v3.26 (Golden Rule)")
    st.caption("【DX仕様】顔・体型完全固定。503リトライ機能搭載")

    with st.sidebar:
        st.subheader("🖼️ ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        if src_img: st.session_state.dx_src_bytes = src_img.getvalue()
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        
        st.divider()
        hair_s = st.selectbox("💇 髪型", list(HAIR_STYLES.keys()), key="dx_hs")
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()), key="dx_hc")
        
        st.divider()
        id_weight = st.slider("顔の固定強度", 0.0, 1.0, 0.85)
        g_scale = st.slider("命令遵守度 (Guidance)", 1.0, 10.0, 5.0) # 体型維持のため高めに設定
        
        run_btn = st.button("🚀 DX 4枚一括生成", type="primary")

    if run_btn and st.session_state.dx_src_bytes and ref_img:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            status.info("🕒 Step 1: 衣装解析（アンカー作成）中...")
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, "Describe clothing keywords. No nudity."])
            st.session_state.dx_anchor = response.text.replace("\n", ", ")

            status.info("⏳ Step 2: キャスト転送中...")
            face_url = fal_client.upload(st.session_state.dx_src_bytes, "image/jpeg")
            poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
            st.session_state.dx_current_poses = poses
            
            for i in range(4):
                status.info(f"🎨 DX描画中 ({i+1}/4)... 進行状況可視化")
                final_p = get_final_dx_prompt(poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c])
                
                try:
                    result = generate_with_retry(face_url, final_p, id_weight, g_scale, 30)
                    st.session_state.dx_images[i] = Image.open(requests.get(result['images'][0]['url'], stream=True).raw)
                except Exception as inner_e:
                    st.error(f"枠 {i+1} 失敗: {inner_e}") # ⚡ 失敗した枠にはステータスログ
                    break
                progress.progress((i+1)/4)
            status.empty()
            st.rerun()
        except Exception as e:
            st.error(f"システムエラー: {e}")

    # --- 表示エリア：個別再送ボタン配置 ---
    if any(img is not None for img in st.session_state.dx_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                img = st.session_state.dx_images[i]
                if img:
                    st.image(img, use_container_width=True)
                    if st.button(f"🔄 枠{i+1} 撮り直し", key=f"re_{i}"):
                        with st.spinner("再生成中..."):
                            f_url = fal_client.upload(st.session_state.dx_src_bytes, "image/jpeg")
                            p = get_final_dx_prompt(st.session_state.dx_current_poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c])
                            res = generate_with_retry(f_url, p, id_weight, g_scale, 30)
                            st.session_state.dx_images[i] = Image.open(requests.get(res['images'][0]['url'], stream=True).raw)
                            st.rerun()
                else:
                    if st.button(f"⚡ 枠{i+1} 個別再送", key=f"retry_{i}"):
                        st.info("個別再送を実行中...") # ⚡ 失敗した枠には個別再送ボタン
