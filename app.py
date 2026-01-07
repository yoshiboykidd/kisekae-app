import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 認証機能 (karin10) ---
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

# --- 2. メインアプリ ---
if check_password():
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)

    st.title("📸 AI KISEKAE [Strict Rule Engine]")

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        src_img = st.file_uploader("1. キャスト写真 (顔・骨格の絶対守護)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装参照写真 (デザイン・柄のみ引用)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. 強制する形 (スタイル)", ["リゾートビキニ", "タイトミニドレス", "清楚ワンピース", "ナースウェア", "バニーガール", "メイドウェア", "浴衣"])
        cloth_detail = st.text_input("追加のこだわり", placeholder="例：黒とピンク、大きなリボンを追加")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "プライベートビーチ"])
        st.divider()
        run_button = st.button("✨ 掟を守って4枚生成")

    if run_button and src_img:
        st.subheader("🖼️ 生成結果 (掟遵守・スタイル融合)")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        base_parts = [types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # プロンプト：命令系統の再構築
        # Image 2を「Garment Shape」ではなく「Fabric DNA」として扱う
        prompt = (
            f"### MANDATORY LAWS (MUST BE FOLLOWED):\n"
            f"1. FACE IDENTITY: The woman's face, features, and bone structure MUST be 100% identical to IMAGE 1. NEVER use the face from IMAGE 2.\n"
            f"2. NO TEETH: In all 4 panels, the woman's lips MUST be sealed. NO TEETH visible. This is a strict rule.\n"
            f"3. OUTFIT SHAPE: The garment MUST be a '{cloth_main}'. Ignore the shape of clothes in IMAGE 2.\n"
            f"4. FABRIC DESIGN: Apply the colors, patterns, and specific decorative style (DNA) from IMAGE 2 onto the '{cloth_main}'. {cloth_detail}.\n\n"
            f"### 2x2 GRID COMPOSITION:\n"
            f"- TOP-LEFT: Full body, standing front pose, lips sealed.\n"
            f"- TOP-RIGHT: Full body, walking side pose, lips sealed.\n"
            f"- BOTTOM-LEFT: Full body, sitting pose, lips sealed.\n"
            f"- BOTTOM-RIGHT: Close-up beauty shot of the face, lips sealed.\n\n"
            f"### TECHNICAL:\n"
            f"Background: {bg} with deep bokeh. 8k resolution, photorealistic masterpiece, sharp focus on subject."
        )

        with st.spinner("掟に従い、デザインを融合中..."):
            try:
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=base_parts + [prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        safety_settings=[
                            types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                            types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                        ],
                        image_config=types.ImageConfig(aspect_ratio="2:3")
                    )
                )

                if response.candidates and response.candidates[0].content.parts:
                    grid_data = response.candidates[0].content.parts[0].inline_data.data
                    full_img = Image.open(io.BytesIO(grid_data))
                    w, h = full_img.size
                    coords = [(0, 0, w//2, h//2), (w//2, 0, w, h//2), (0, h//2, w//2, h), (w//2, h//2, w, h)]
                    labels = ["正面全身", "動き全身", "座り姿", "顔寄り"]
                    
                    for i, coord in enumerate(coords):
                        with placeholders[i]:
                            cropped = full_img.crop(coord).resize((600, 900))
                            st.image(cropped, caption=labels[i], use_container_width=True)
                            
                            buf = io.BytesIO()
                            cropped.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p{i+1}.jpg", mime="image/jpeg", key=f"btn_{i}")
                else:
                    st.error("AI規制によりブロックされました。")
            except Exception as e:
                st.error(f"エラー: {e}")

st.markdown("---")
st.caption("© 2026 Karinto Group - Strict Rule Engine V1")
