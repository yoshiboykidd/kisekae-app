import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os
from PIL import Image

# --- 1. 定義データ (日本人女性・実写特化) [cite: 2026-01-16] ---
HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft wavy curls", "ハーフアップ": "half-up", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "original color", "ナチュラルブラック": "black", "ダークブラウン": "dark brown", "ashベージュ": "ash beige", "ミルクティーグレージュ": "greige", "ピンクブラウン": "pink brown", "ハニーブロンド": "honey blonde"}
STAND_PROMPTS = ["Full body, leaning against a wall", "Full body, walking", "Full body, weight on one leg", "Full body, looking over shoulder", "Full body, adjusting hair", "Full body, 3/4 view"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways", "Full body, sitting on steps", "Full body, legs crossed", "Full body, leaning forward on chair"]

# --- 2. プロンプトエンジン (衣装優先配置) [cite: 2026-01-16] ---
def get_final_dx_prompt(pose, anchor_text, hair_s, hair_c, id_weight):
    identity_lock = (
        "CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK [cite: 2026-01-16]. "
        "STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK [cite: 2026-01-16]. "
        "Match EXACT face and body mass of IMAGE 1 [cite: 2026-01-16]. "
    )
    # 衣装指示を前方に配置して反映率をアップ
    wardrobe_section = f"WARDROBE: {anchor_text}, high-quality fabric texture, realistic fit. "
    render_recipe = (
        "Subject: Japanese woman [cite: 2025-12-30]. "
        "Hyper-realistic photo, Sony A7R IV, 35mm lens, f/2.8, "
        "detailed skin pores, cinematic lighting, 8k, film grain [cite: 2026-01-16]."
    )
    return f"{identity_lock} {wardrobe_section} POSE: {pose}. HAIR: {hair_s}, Color: {hair_c}. {render_recipe}"

# --- 3. UI メイン処理 ---
def show_dx_ui():
    if "GEMINI_API_KEY" not in st.secrets or "FAL_KEY" not in st.secrets:
        st.error("🔑 APIキーが Secrets に設定されていません。")
        st.stop()
    
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_anchor" not in st.session_state: st.session_state.dx_anchor = ""
    if "dx_src_bytes" not in st.session_state: st.session_state.dx_src_bytes = None

    st.header("💎 AI KISEKAE DX v3.20")

    with st.sidebar:
        st.subheader("🖼️ 画像ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        if src_img: st.session_state.dx_src_bytes = src_img.getvalue()
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        
        st.divider()
        cloth_note = st.text_input("衣装の追加補足", placeholder="例: shiny leather")
        hair_s = st.selectbox("💇 髪型", list(HAIR_STYLES.keys()), key="dx_hs")
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()), key="dx_hc")
        
        st.divider()
        st.subheader("⚙️ パラメータ調整")
        id_weight = st.slider("顔の固定強度", 0.0, 1.0, 0.82)
        g_scale = st.slider("命令遵守度 (Guidance)", 1.0, 10.0, 5.0, help="衣装が出ない時は 5.5 以上へ")
        
        run_btn = st.button("🚀 DX 4枚一括生成", type="primary")

    # アンカー確認用
    if st.session_state.dx_anchor:
        with st.expander("📝 抽出された衣装設計図 (Anchor)"):
            st.info(st.session_state.dx_anchor)

    if run_btn and st.session_state.dx_src_bytes and ref_img:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            # Step 1: 解析
            status.info("🕒 Step 1/2: 衣装を解析中...")
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            analysis_p = f"Describe clothing ONLY in keywords. {cloth_note}"
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, analysis_p])
            st.session_state.dx_anchor = response.text

            # Step 2: 描画
            status.info("⏳ Step 2/2: Fal.ai 描画エンジンを起動...")
            face_url = fal_client.upload(st.session_state.dx_src_bytes, "image/jpeg")
            poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
            st.session_state.dx_current_poses = poses
            
            for i in range(4):
                status.info(f"🎨 描画中 ({i+1}/4)...")
                final_p = get_final_dx_prompt(poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], id_weight)
                
                try:
                    result = fal_client.subscribe("fal-ai/flux-pulid", arguments={
                        "prompt": final_p, "reference_image_url": face_url,
                        "id_weight": id_weight, "guidance_scale": g_scale,
                        "num_inference_steps": 30, "enable_safety_checker": False
                    })
                    image_url = result['images'][0]['url']
                    st.session_state.dx_images[i] = Image.open(requests.get(image_url, stream=True).raw)
                except Exception as inner_e:
                    # 🔴 ここでエラーをメイン画面にしっかり出す
                    st.error(f"❌ 枠 {i+1} の生成に失敗しました。\n\n理由: {str(inner_e)}")
                    if "Insufficient funds" in str(inner_e):
                        st.warning("💳 Fal.ai の残高が不足しています！チャージが必要です。")
                    break
                progress.progress((i+1)/4)
            status.empty()
            st.rerun()
        except Exception as e:
            st.error(f"🚫 システムエラー: {e}")

    # --- 表示・個別撮り直し ---
    if any(img is not None for img in st.session_state.dx_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                img = st.session_state.dx_images[i]
                if img:
                    st.image(img, use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"dx_{i}.jpg", "image/jpeg", key=f"dl_{i}")
                    if st.button("🔄 この枠だけ撮り直し", key=f"re_{i}"):
                        with st.spinner("DX再描画中..."):
                            try:
                                face_u = fal_client.upload(st.session_state.dx_src_bytes, "image/jpeg")
                                pr = get_final_dx_prompt(st.session_state.dx_current_poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], id_weight)
                                res = fal_client.subscribe("fal-ai/flux-pulid", arguments={"prompt": pr, "reference_image_url": face_u, "id_weight": id_weight, "guidance_scale": g_scale, "num_inference_steps": 30, "enable_safety_checker": False})
                                st.session_state.dx_images[i] = Image.open(requests.get(res['images'][0]['url'], stream=True).raw)
                                st.rerun()
                            except Exception as e: st.error(f"再生成失敗: {e}")
