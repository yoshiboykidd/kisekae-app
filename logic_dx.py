import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os, time
from PIL import Image

# --- 1. 定義データ (日本人女性・実写ポーズ特化) ---
STAND_PROMPTS = ["Full body, leaning against a wall", "Full body, walking slowly", "Full body, weight on one leg", "Full body, 3/4 view, elegant posture"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways on chair", "Full body, sitting on steps", "Full body, legs crossed"]

# --- 2. プロンプトエンジン (黄金律 2.66 準拠：体型死守・露出防止) ---
def get_final_dx_prompt(pose, anchor_text):
    # 体型固定を最優先。美化と痩身を徹底禁止
    identity_lock = (
        "STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK. "
        "Match the EXACT silhouette, shoulder width, and realistic body mass from IMAGE 1. "
        "Do NOT thin the waist, do NOT lengthen the legs. No beautification. "
        "Maintain the realistic fleshiness of a Japanese woman. "
    )
    # 衣装（裸化防止：Night-fashion フィルター）
    wardrobe = f"WARDROBE: {anchor_text}, solid non-transparent fabric, opaque material, realistic clothing folds. "
    render = (
        "Hyper-realistic photography, Sony A7R IV, 35mm lens, f/2.8, cinematic lighting, 8k, film grain."
    )
    return f"{identity_lock} {wardrobe} POSE: {pose}. {render}"

# --- 3. UI メイン処理 ---
def show_dx_ui():
    if "GEMINI_API_KEY" not in st.secrets or "FAL_KEY" not in st.secrets:
        st.error("🔑 APIキーが Secrets に未設定です。")
        st.stop()
    
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    # セッション状態の初期化
    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_last_error" not in st.session_state: st.session_state.dx_last_error = None

    st.header("💎 AI KISEKAE DX v3.32 (Final Body Lock)")

    # 🔴 エラー表示エリア（rerunしても消えないように固定）
    if st.session_state.dx_last_error:
        st.error(f"❌ 生成エラーが発生しました:\n\n{st.session_state.dx_last_error}")
        if st.button("エラー表示を消去して再開"):
            st.session_state.dx_last_error = None
            st.rerun()

    with st.sidebar:
        st.subheader("🖼️ 画像ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        st.divider()
        st.subheader("⚙️ 調整")
        id_weight = st.slider("顔の固定強度", 0.0, 1.0, 0.82)
        # 衣装無視を防ぐために初期値を 6.5 まで引き上げ
        g_scale = st.slider("命令遵守度 (Guidance)", 1.0, 10.0, 6.5)
        run_btn = st.button("🚀 DX鉄壁一括生成", type="primary")

    if run_btn and src_img and ref_img:
        st.session_state.dx_images = [None] * 4
        st.session_state.dx_last_error = None
        status = st.empty(); progress = st.progress(0)
        
        try:
            # Step 1: 解析
            status.info("🕒 Step 1/2: 衣装デザインを解析中...")
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            analysis_p = "Describe clothing keywords ONLY. Material, color, cut. No nudity."
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, analysis_p])
            anchor = response.text.replace("\n", ", ")

            # Step 2: 描画 (Cannyによる物理体型固定)
            status.info("⏳ Step 2/2: Fal.ai 描画エンジンを起動...")
            src_bytes = src_img.getvalue()
            src_url = fal_client.upload(src_bytes, "image/jpeg")
            poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
            
            for i in range(4):
                status.info(f"🎨 物理固定描画中 ({i+1}/4)...")
                final_p = get_final_dx_prompt(poses[i], anchor)
                
                try:
                    # PuLIDによる顔固定 + Cannyによる体型固定のハイブリッド
                    result = fal_client.subscribe(
                        "fal-ai/flux-pulid",
                        arguments={
                            "prompt": final_p,
                            "reference_image_url": src_url,
                            "id_weight": id_weight,
                            "guidance_scale": g_scale,
                            "num_inference_steps": 35,
                            "enable_safety_checker": False,
                            # 物理的に輪郭を縛る設定（IMAGE 1 の形をなぞらせる）
                            "controlnet_type": "canny",
                            "controlnet_image_url": src_url,
                            "controlnet_conditioning_scale": 0.85 # 1.0に近づけるほど体型が固定
                        }
                    )
                    image_url = result['images'][0]['url']
                    st.session_state.dx_images[i] = Image.open(requests.get(image_url, stream=True).raw)
                except Exception as inner_e:
                    # 🔴 rerunを呼び出さず、エラーをセッションに保存して停止
                    st.session_state.dx_last_error = str(inner_e)
                    break
                progress.progress((i+1)/4)
            
            status.empty()
            # 🔴 全て成功した時だけ再描画
            if not st.session_state.dx_last_error:
                st.rerun()

        except Exception as e:
            st.session_state.dx_last_error = f"システム全体エラー: {str(e)}"
            st.rerun()

    # --- 表示エリア ---
    if any(img is not None for img in st.session_state.dx_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                if st.session_state.dx_images[i]:
                    st.image(st.session_state.dx_images[i], use_container_width=True)
                    buf = io.BytesIO(); st.session_state.dx_images[i].save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"dx_{i}.jpg", key=f"dl_{i}")
