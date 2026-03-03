import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os
from PIL import Image

# --- 1. 定義データ (完全移植) [cite: 2026-01-16] ---
HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft loose curls", "ハーフアップ": "half-up", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "original hair color", "ナチュラルブラック": "black hair", "ダークブラウン": "dark brown hair", "ashベージュ": "ash beige", "ミルクティーグレージュ": "greige", "ピンクブラウン": "pink brown", "ハニーブロンド": "honey blonde"}
STAND_PROMPTS = ["Full body, leaning against a wall", "Full body, walking slowly", "Full body, weight on one leg", "Full body, looking over shoulder", "Full body, adjusting hair", "Full body, 3/4 view"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways", "Full body, sitting on steps", "Full body, legs crossed", "Full body, leaning forward on chair"]

# --- 2. プロンプトエンジン (インペインティング専用) [cite: 2026-01-16] ---
def get_final_dx_prompt(pose, anchor_text, hair_s, hair_c):
    # 体型を100%守るためのインペインティング専用命令 [cite: 2026-01-16]
    security_lock = (
        "CRITICAL: ABSOLUTE BODY VOLUME LOCK [cite: 2026-01-16]. "
        "The subject is a completely clothed Japanese woman [cite: 2025-12-30]. "
        "WARDROBE: solid non-transparent fabric, opaque material [cite: 2026-01-16]. "
        "No nudity, no exposure. Integrate the subject clothing onto the base image seamlessly [cite: 2026-01-16]. "
    )
    render_recipe = (
        "Subject: Japanese woman [cite: 2025-12-30]. "
        "Hyper-realistic photography, Sony A7R IV, 35mm lens, f/2.8, "
        "detailed skin pores, cinematic lighting, 8k, film grain [cite: 2026-01-16]."
    )
    return f"{security_lock} POSE: {pose}. HAIR: {hair_s}, Color: {hair_c}. WARDROBE DESCRIPTION: {anchor_text}. {render_recipe}"

# --- 3. UI メイン処理 ---
def show_dx_ui():
    if "GEMINI_API_KEY" not in st.secrets or "FAL_KEY" not in st.secrets:
        st.error("🔑 APIキーが Secrets に未設定です。")
        st.stop()
    
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    # セッション状態の初期化
    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_anchor" not in st.session_state: st.session_state.dx_anchor = ""
    if "dx_error" not in st.session_state: st.session_state.dx_error = None

    st.header("💎 AI KISEKAE DX v3.23 (Inpainting Debug)")

    # 永続的なエラー表示エリア
    if st.session_state.dx_error:
        st.error(f"❌ 前回の実行でエラーが発生しました:\n\n{st.session_state.dx_error}")
        if st.button("エラーをクリア"):
            st.session_state.dx_error = None
            st.rerun()

    with st.sidebar:
        st.subheader("🖼️ 画像ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        
        st.divider()
        st.subheader("💇 スタイル設定")
        hair_s = st.selectbox("髪型", list(HAIR_STYLES.keys()), key="dx_hs")
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()), key="dx_hc")
        
        st.divider()
        st.subheader("⚙️ パラメータ")
        g_scale = st.slider("命令遵守度 (Guidance)", 1.0, 10.0, 3.5)
        steps = st.slider("描き込み回数 (Steps)", 20, 50, 35)
        
        run_btn = st.button("🚀 DX鉄壁一括生成", type="primary")

    if run_btn and src_img and ref_img:
        st.session_state.dx_images = [None] * 4
        st.session_state.dx_error = None # エラーリセット
        status = st.empty(); progress = st.progress(0)
        
        try:
            status.info("🕒 Step 1/2: 衣装を解析中...")
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            analysis_p = "Describe the clothing ONLY in keywords. Focus on material and cut. No sentences."
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, analysis_p])
            st.session_state.dx_anchor = response.text

            status.info("⏳ Step 2/2: Fal.ai 描画エンジンを起動...")
            src_bytes = src_img.getvalue()
            ref_bytes = ref_img.getvalue()
            src_url = fal_client.upload(src_bytes, "image/jpeg")
            ref_url = fal_client.upload(ref_bytes, "image/jpeg")
            
            poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
            
            for i in range(4):
                status.info(f"🎨 描画中 ({i+1}/4)...")
                final_p = get_final_dx_prompt(poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c])
                
                try:
                    # Inpainting 方式で体型を 100% 維持 [cite: 2026-01-16, 2026-03-01]
                    result = fal_client.subscribe(
                        "fal-ai/flux-subject-inpainting",
                        arguments={
                            "base_image_url": src_url,
                            "subject_image_url": ref_url,
                            "subject_category": "clothing",
                            "prompt": final_p,
                            "mask_grow": 25,
                            "num_inference_steps": steps,
                            "guidance_scale": g_scale,
                            "enable_safety_checker": False
                        }
                    )
                    image_url = result['images'][0]['url']
                    st.session_state.dx_images[i] = Image.open(requests.get(image_url, stream=True).raw)
                except Exception as inner_e:
                    # 🔴 エラーをセッションに保存してループを抜ける
                    st.session_state.dx_error = str(inner_e)
                    break
                progress.progress((i+1)/4)
            
            status.empty()
            # 🔴 エラーがなければリロードして表示
            if not st.session_state.dx_error:
                st.rerun()
            else:
                # 🔴 エラーがあればそのまま画面を止め、エラーを表示
                st.error("生成中にエラーが発生しました。上記のエラーメッセージを確認してください。")

        except Exception as e:
            st.session_state.dx_error = f"システム全体エラー: {str(e)}"
            st.rerun()

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
