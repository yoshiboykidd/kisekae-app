import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os
from PIL import Image

# ... (髪型・ポーズ等の定義データは前回と同じため省略) ...
HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft loose wavy curls", "ハーフアップ": "half-up", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "original color", "ナチュラルブラック": "black", "ダークブラウン": "dark brown", "ashベージュ": "ash beige", "ミルクティーグレージュ": "greige", "ピンクブラウン": "pink brown", "ハニーブロンド": "honey blonde"}
STAND_PROMPTS = ["Full body, leaning against a wall", "Full body, walking", "Full body, weight on one leg", "Full body, looking over shoulder", "Full body, adjusting hair", "Full body, 3/4 view"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways", "Full body, sitting on steps", "Full body, legs crossed", "Full body, leaning forward on chair"]

def get_final_dx_prompt(pose, anchor_text, hair_s, hair_c, id_weight):
    # 黄金律：顔と体型を最優先 [cite: 2026-01-16]
    identity_lock = (
        "CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK [cite: 2026-01-16]. "
        "STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK [cite: 2026-01-16]. "
        "Match EXACT face and body mass of IMAGE 1. 100% identity match [cite: 2026-01-16]. "
    )
    # 反映率向上のため、WARDROBEを前方に配置
    wardrobe_section = f"WARDROBE: {anchor_text}, realistic fabric texture, perfect fit. "
    
    render_recipe = (
        "Subject is a Japanese woman [cite: 2025-12-30]. "
        "Hyper-realistic photography, Sony A7R IV, 35mm lens, f/2.8, "
        "highly detailed skin pores, cinematic lighting, 8k, film grain [cite: 2026-01-16]."
    )
    # 全体を統合
    return f"{identity_lock} {wardrobe_section} POSE: {pose}. HAIR: {hair_s}, Color: {hair_c}. {render_recipe}"

def show_dx_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_anchor" not in st.session_state: st.session_state.dx_anchor = ""

    st.header("💎 AI KISEKAE DX v3.19 (High Reflectivity)")

    with st.sidebar:
        st.subheader("🖼️ 画像ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        
        st.divider()
        cloth_note = st.text_input("衣装の追加補足", placeholder="例: black leather, shiny")
        hair_s = st.selectbox("💇 髪型", list(HAIR_STYLES.keys()), key="dx_hs")
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()), key="dx_hc")
        
        st.divider()
        st.subheader("⚙️ パラメータ調整")
        id_weight = st.slider("顔の固定強度", 0.0, 1.0, 0.82)
        g_scale = st.slider("命令遵守度 (Guidance)", 1.0, 10.0, 4.5, help="衣装が反映されない場合は5.0以上に上げてください。")
        
        run_btn = st.button("🚀 DX 4枚一括生成", type="primary")

    # アンカーのプレビュー（デバッグ用）
    if st.session_state.dx_anchor:
        with st.expander("📝 現在の衣装アンカー（設計図）を確認"):
            st.code(st.session_state.dx_anchor)

    if run_btn and src_img and ref_img:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            # Step 1: Geminiによる高精度アンカー作成 [cite: 2026-01-16]
            status.info("🕒 Step 1/2: 衣装のデザインを解析中...")
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            # 箇条書きキーワードのみを出力させるためのプロンプト
            analysis_p = (
                "Describe the clothing in the image. Output ONLY short descriptive keywords "
                "separated by commas. Focus on material, specific cut, and colors. "
                "Example: 'black satin bunny suit, white cuffs, mesh stockings'. "
                f"Additional info: {cloth_note}"
            )
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, analysis_p])
            st.session_state.dx_anchor = response.text.replace("\n", ", ") # 改行を消してカンマ区切りに

            # Step 2: Fal.ai描画
            status.info("⏳ 描画エンジンを起動中...")
            face_url = fal_client.upload(src_img.getvalue(), "image/jpeg")
            poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
            
            for i in range(4):
                status.info(f"🎨 DX描画中 ({i+1}/4)...")
                final_p = get_final_dx_prompt(poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], id_weight)
                
                result = fal_client.subscribe("fal-ai/flux-pulid", arguments={
                    "prompt": final_p, "reference_image_url": face_url,
                    "id_weight": id_weight, "guidance_scale": g_scale,
                    "num_inference_steps": 30, "enable_safety_checker": False
                })
                st.session_state.dx_images[i] = Image.open(requests.get(result['images'][0]['url'], stream=True).raw)
                progress.progress((i+1)/4)
            st.rerun() # 画面を更新してアンカープレビューを表示
        except Exception as e:
            st.error(f"🚫 エラー: {e}")
