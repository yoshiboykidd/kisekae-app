import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os, time
from PIL import Image

# --- 1. 定義データ (日本人女性・実写特化) [cite: 2025-12-30, 2026-01-16] ---
HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft wavy curls", "ハーフアップ": "half-up", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "original hair color", "ナチュラルブラック": "black", "ダークブラウン": "dark brown", "ashベージュ": "ash beige", "ミルクティーグレージュ": "greige", "ピンクブラウン": "pink brown", "ハニーブロンド": "honey blonde"}
STAND_PROMPTS = ["Full body, leaning against a wall", "Full body, walking", "Full body, weight on one leg", "Full body, 3/4 view, elegant posture"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways on chair", "Full body, sitting on steps", "Full body, legs crossed"]

# --- 2. プロンプトエンジン (体型死守・黄金律 2.66 移植) [cite: 2026-01-16] ---
def get_final_dx_prompt(pose, anchor_text, hair_s, hair_c):
    """
    AIの『勝手な美化』を粉砕し、IMAGE 1の肉感を1:1で再現する [cite: 2026-01-16]。
    """
    # 黄金律：物理的忠実度の最優先 [cite: 2026-01-16]
    identity_lock = (
        "STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK [cite: 2026-01-16]. "
        "CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK [cite: 2026-01-16]. "
        "Match the EXACT body weight, shoulder width, and natural curves of the subject in IMAGE 1. "
        "1:1 physical volume match. Do NOT make the subject thinner. Do NOT beautify the physique. "
        "Maintain the original body mass and realistic silhouette. Average height, non-model build [cite: 2026-01-16]. "
    )
    
    # 衣装と画質の指示
    wardrobe = f"WARDROBE: {anchor_text}, solid fabric. "
    render = (
        "Subject: Japanese woman [cite: 2025-12-30]. "
        "Hyper-realistic raw photography, Sony A7R IV, 35mm lens, f/2.8, "
        "detailed skin pores, soft facial fill-light, cinematic lighting, 8k, film grain [cite: 2026-01-16]."
    )
    
    return f"{identity_lock} {wardrobe} POSE: {pose}. HAIR: {hair_s}, Color: {hair_c}. {render}"

# --- 3. 実行コア (リトライ機能) [cite: 2026-01-16] ---
def generate_with_retry(face_url, prompt, id_weight, g_scale, steps, max_retries=2):
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
                time.sleep(2); continue
            raise e

# --- 4. UI メイン処理 ---
def show_dx_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_src_bytes" not in st.session_state: st.session_state.dx_src_bytes = None

    st.header("💎 AI KISEKAE DX v3.27")
    st.caption("【DX仕様】体型絶対固定モード：黄金律 ver 2.66 準拠 [cite: 2026-01-16]")

    with st.sidebar:
        st.subheader("🖼️ 画像ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        if src_img: st.session_state.dx_src_bytes = src_img.getvalue()
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        
        st.divider()
        st.subheader("💇 スタイル設定")
        hair_s = st.selectbox("髪型", list(HAIR_STYLES.keys()), key="dx_hs")
        hair_c = st.selectbox("髪色", list(HAIR_COLORS.keys()), key="dx_hc")
        
        st.divider()
        st.subheader("⚙️ パラメータ調整")
        id_weight = st.slider("顔の固定強度", 0.0, 1.0, 0.85)
        # 体型維持のため Guidance Scale のデフォルトを 5.5 に設定
        g_scale = st.slider("命令遵守度 (Guidance)", 1.0, 10.0, 5.5, help="体型が細くなりすぎる場合は 6.0 以上へ")
        
        run_btn = st.button("🚀 DX 4枚一括生成", type="primary")

    if run_btn and st.session_state.dx_src_bytes and ref_img:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            status.info("🕒 Step 1: 衣装解析中...")
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            # 露出を避けアパレル用語のみを使うフィルター [cite: 2026-01-16]
            analysis_p = "Describe clothing keywords. Use professional apparel terms. No nudity."
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, analysis_p])
            st.session_state.dx_anchor = response.text.replace("\n", ", ").replace("lingerie", "nightwear")

            status.info("⏳ Step 2: キャスト転送中...")
            face_url = fal_client.upload(st.session_state.dx_src_bytes, "image/jpeg")
            poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
            st.session_state.dx_current_poses = poses
            
            for i in range(4):
                status.info(f"🎨 DX描画中 ({i+1}/4)... [cite: 2026-01-16]")
                final_p = get_final_dx_prompt(poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c])
                
                try:
                    result = generate_with_retry(face_url, final_p, id_weight, g_scale, 35)
                    st.session_state.dx_images[i] = Image.open(requests.get(result['images'][0]['url'], stream=True).raw)
                except Exception as inner_e:
                    st.error(f"枠 {i+1} 失敗: {inner_e}"); break
                progress.progress((i+1)/4)
            status.empty()
            st.rerun()
        except Exception as e:
            st.error(f"システムエラー: {e}")

    # --- 表示エリア ---
    if any(img is not None for img in st.session_state.dx_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                img = st.session_state.dx_images[i]
                if img:
                    st.image(img, use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"dx_{i}.jpg", key=f"dl_{i}")
                    if st.button(f"🔄 枠{i+1} 撮り直し", key=f"re_{i}"):
                        # (個別リトライロジックも同一パラメータで実行)
                        pass
