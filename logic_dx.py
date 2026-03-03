import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os, time
from PIL import Image

# --- 1. 定義データ (ポーズ・スタイル) [cite: 2026-01-16] ---
HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft wavy curls", "ハーフアップ": "half-up", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "original color", "ナチュラルブラック": "black", "ダークブラウン": "dark brown", "ashベージュ": "ash beige", "ミルクティーグレージュ": "greige", "ピンクブラウン": "pink brown", "ハニーブロンド": "honey blonde"}
STAND_PROMPTS = ["Full body, leaning against a wall", "Full body, walking", "Full body, weight on one leg", "Full body, 3/4 view, elegant posture"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways", "Full body, sitting on steps", "Full body, legs crossed"]

# --- 2. 物理固定エンジン (Canny + Identity Lock) [cite: 2026-01-16] ---
def get_final_dx_prompt(pose, anchor_text, hair_s, hair_c):
    """
    体型を輪郭レベルで固定し、衣装を優先させるプロンプト [cite: 2026-01-16]。
    """
    # 黄金律：物理的忠実度を最優先 [cite: 2026-01-16]
    identity_lock = (
        "STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK [cite: 2026-01-16]. "
        "Match the EXACT silhouette, shoulder width, and realistic curves from the Canny mask. "
        "No beautification, no thinning. Maintain the subject's original body mass [cite: 2026-01-16]. "
    )
    # 衣装と画質（露出防止フィルター [cite: 2026-01-16]）
    wardrobe = f"WARDROBE: {anchor_text}, high-quality fabric, non-transparent. "
    render = (
        "Subject: Japanese woman [cite: 2025-12-30]. "
        "Hyper-realistic raw photography, Sony A7R IV, 35mm lens, f/2.8, cinematic lighting, 8k, film grain [cite: 2026-01-16]."
    )
    return f"{identity_lock} {wardrobe} POSE: {pose}. HAIR: {hair_s}, Color: {hair_c}. {render}"

def generate_with_retry(face_url, prompt, id_weight, g_scale, steps, max_retries=2):
    """黄金律：503エラーリトライ機能 [cite: 2026-01-16]"""
    for attempt in range(max_retries + 1):
        try:
            # flux-pulid で Canny（輪郭固定）を併用する設定
            return fal_client.subscribe(
                "fal-ai/flux-pulid",
                arguments={
                    "prompt": prompt,
                    "reference_image_url": face_url,
                    "id_weight": id_weight,
                    "guidance_scale": g_scale,
                    "num_inference_steps": steps,
                    "enable_safety_checker": False,
                    # ここで IMAGE 1 を輪郭固定用としても使用する
                    "controlnet_type": "canny",
                    "controlnet_image_url": face_url, 
                    "controlnet_conditioning_scale": 0.8 # 強めに輪郭を守らせる
                }
            )
        except Exception as e:
            if "503" in str(e) and attempt < max_retries:
                time.sleep(2); continue
            raise e

# --- 3. UI メイン処理 ---
def show_dx_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_src_bytes" not in st.session_state: st.session_state.dx_src_bytes = None

    st.header("💎 AI KISEKAE DX v3.28 (Body Lock)")
    st.caption("【DX仕様】Canny輪郭固定。キャストの肉感を100%維持します [cite: 2026-01-16]")

    with st.sidebar:
        st.subheader("🖼️ 画像ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        if src_img: st.session_state.dx_src_bytes = src_img.getvalue()
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        
        st.divider()
        st.subheader("💇 スタイル設定")
        hair_s = st.selectbox("髪型", list(HAIR_STYLES.keys()), key="dx_hs")
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()), key="dx_hc")
        cloth_note = st.text_input("衣装の追加補足", placeholder="例: black satin, opaque")
        
        st.divider()
        st.subheader("⚙️ パラメータ調整")
        id_weight = st.slider("顔の固定強度", 0.0, 1.0, 0.82)
        # 衣装を無視させないために初期値を 6.0 に引き上げ [cite: 2026-03-01]
        g_scale = st.slider("命令遵守度 (Guidance)", 1.0, 10.0, 6.0)
        
        run_btn = st.button("🚀 DX鉄壁一括生成", type="primary")

    if run_btn and st.session_state.dx_src_bytes and ref_img:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            status.info("🕒 Step 1: 衣装解析（アンカー作成）中...")
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            analysis_p = f"Analyze clothing in keywords ONLY. Material, shape, color. {cloth_note}"
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, analysis_p])
            st.session_state.dx_anchor = response.text.replace("\n", ", ")

            status.info("⏳ Step 2: 描画エンジン起動中...")
            face_url = fal_client.upload(st.session_state.dx_src_bytes, "image/jpeg")
            poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
            st.session_state.dx_current_poses = poses
            
            for i in range(4):
                status.info(f"🎨 DX一括生成中 ({i+1}/4)... 進行状況可視化 [cite: 2026-01-16]")
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

    # --- 表示エリア：個別ボタン配置 [cite: 2026-01-16] ---
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
                        with st.spinner("再生成中..."):
                            f_url = fal_client.upload(st.session_state.dx_src_bytes, "image/jpeg")
                            p = get_final_dx_prompt(st.session_state.dx_current_poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c])
                            res = generate_with_retry(f_url, p, id_weight, g_scale, 35)
                            st.session_state.dx_images[i] = Image.open(requests.get(res['images'][0]['url'], stream=True).raw)
                            st.rerun()
