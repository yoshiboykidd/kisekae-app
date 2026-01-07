import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 認証機能 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 Karinto Group Image Tool")
        pwd = st.text_input("合言葉を入力してください", type="password")
        if st.button("ログイン"):
            if pwd == "karin10": 
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("合言葉が正しくありません")
        return False
    return True

if check_password():
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)

    st.title("📸 AI KISEKAE [Master Anchor Mode]")

    POSE_LIBRARY = {
        "Standard (王道)": ["Full body standing front.", "Walking toward camera.", "Sitting on stool.", "Leaning against wall."],
        "Cool & Sexy (大胆)": ["Low angle sharp gaze.", "Sitting on floor leaning back.", "Back view over shoulder.", "Lying on luxury sofa."],
        "Cute & Active (動き)": ["Jumping slightly.", "Twirling skirt expanding.", "Kneeling on carpet.", "Crouching and peeking."]
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        src_img = st.file_uploader("1. キャスト写真 (顔の絶対ソース)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装写真 (デザインの見本)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. 強制スタイル", ["リゾートビキニ", "タイトミニドレス", "清楚ワンピース", "ナース服", "バニーガール", "メイド服", "浴衣"])
        cloth_detail = st.text_input("追加の指示", placeholder="例：黒サテン、赤リボン")
        vibe_choice = st.selectbox("4. Vibe (ポーズ系統)", list(POSE_LIBRARY.keys()))
        bg = st.selectbox("5. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "ビーチ"])
        st.divider()
        run_button = st.button("✨ 衣装を固定して4枚一括生成")

    if run_button and src_img:
        selected_poses = POSE_LIBRARY[vibe_choice]
        st.subheader(f"🖼️ 生成結果 [{vibe_choice}]")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        base_parts = [types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # 衣装指示を「完全コピー」ベースに変更
        if ref_img:
            outfit_logic = (
                f"Identify the exact design from IMAGE 2. Create a '{cloth_main}' version of it. "
                f"Zero tolerance for detail changes across panels. {cloth_detail}."
            )
        else:
            outfit_logic = f"Outfit: {cloth_main}. {cloth_detail}."

        # 【新・アンカープロンプト】: 1枚目をマスターとして残りの整合性をとらせる
        prompt = (
            f"SYSTEM: This is a 2x2 grid image. Each panel must have consistent identity.\n"
            f"1. PANEL 1 (TOP-LEFT) is the MASTER REFERENCE. Create the woman from IMAGE 1 in this {cloth_main}.\n"
            f"2. PANELS 2, 3, AND 4 MUST CLONE THE OUTFIT FROM PANEL 1 EXACTLY. Every button, ribbon, and pattern must be identical.\n"
            f"IDENTITY: Strictly use IMAGE 1's face and bone structure for ALL panels.\n"
            f"RULE: Lips sealed, no teeth visible in all photos.\n"
            f"POSES: [TL: {selected_poses[0]}], [TR: {selected_poses[1]}], [BL: {selected_poses[2]}], [BR: {selected_poses[3]}].\n"
            f"ENVIRONMENT: {bg}. 8k photorealistic studio photography."
        )

        with st.spinner("マスター衣装を定義し、4枚を同期中..."):
            try:
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=base_parts + [prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')],
                        image_config=types.ImageConfig(aspect_ratio="2:3")
                    )
                )

                if response.candidates and response.candidates[0].content.parts:
                    grid_data = response.candidates[0].content.parts[0].inline_data.data
                    full_img = Image.open(io.BytesIO(grid_data))
                    w, h = full_img.size
                    coords = [(0, 0, w//2, h//2), (w//2, 0, w, h//2), (0, h//2, w//2, h), (w//2, h//2, w, h)]
                    
                    for i, coord in enumerate(coords):
                        with placeholders[i]:
                            cropped = full_img.crop(coord).resize((600, 900))
                            st.image(cropped, use_container_width=True)
                            buf = io.BytesIO()
                            cropped.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p{i+1}.jpg", mime="image/jpeg", key=f"dl_{i}")
                else:
                    st.error("生成失敗")
            except Exception as e:
                st.error(f"システムエラー: {e}")

st.markdown("---")
st.caption("© 2026 Karinto Group - Master Anchor Engine")
