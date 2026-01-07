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

    st.title("📸 AI KISEKAE [Identity Lock V2]")

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        src_img = st.file_uploader("1. キャスト写真 (顔・骨格：100%遵守)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装写真 (布の柄・色のみ引用)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル", ["ワンピースドレス", "タイトミニドレス", "オフィスカジュアル", "ナースウェア", "メイドウェア", "サマー・リゾートウェア", "浴衣"])
        cloth_detail = st.text_input("追加指示", placeholder="例：黒サテン地、ピンクのリボン")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "サマー・リゾート地"])
        st.divider()
        run_button = st.button("✨ 顔を固定して一括生成")

    if run_button and src_img:
        st.subheader("🖼️ 生成結果")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        base_parts = [types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # AIへの役割分担を「人間」と「物体」に完全に切り分けるプロンプト
        prompt = (
            f"STRICT ROLE ASSIGNMENT:\n"
            f"1. SUBJECT: The woman in IMAGE 1 is the ONLY subject. Her face, facial features, and bone structure MUST be 100% identical to IMAGE 1 in all panels.\n"
            f"2. REFERENCE: IMAGE 2 is NOT a person. Treat IMAGE 2 ONLY as a texture and color pattern for the fabric.\n"
            f"3. OUTFIT: Wear a {cloth_main} using the exact pattern and DNA from IMAGE 2. {cloth_detail}.\n"
            f"4. RULES: LIPS SEALED, NO TEETH. Consistent identity across 4 panels.\n\n"
            f"POSES IN 2x2 GRID:\n"
            f"- Top-Left: Full body standing front.\n"
            f"- Top-Right: Full body walking side.\n"
            f"- Bottom-Left: Full body sitting elegantly.\n"
            f"- Bottom-Right: Face close-up portrait.\n\n"
            f"QUALITY: Photorealistic 8k, professional studio lighting, sharp focus. Background: {bg}."
        )

        with st.spinner("キャストの顔をロックして生成中..."):
            try:
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=base_parts + [prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        safety_settings=[
                            types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                        ],
                        image_config=types.ImageConfig(aspect_ratio="2:3")
                    )
                )

                if response.candidates and response.candidates[0].content.parts:
                    grid_data = response.candidates[0].content.parts[0].inline_data.data
                    full_img = Image.open(io.BytesIO(grid_data))
                    w, h = full_img.size
                    coords = [(0, 0, w//2, h//2), (w//2, 0, w, h//2), (0, h//2, w//2, h), (w//2, h//2, w, h)]
                    labels = ["正面", "動き", "座り姿", "顔寄り"]
                    
                    for i, coord in enumerate(coords):
                        with placeholders[i]:
                            cropped = full_img.crop(coord).resize((600, 900))
                            st.image(cropped, caption=labels[i], use_container_width=True)
                            
                            buf = io.BytesIO()
                            cropped.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p{i+1}.jpg", mime="image/jpeg", key=f"btn_{i}")
                else:
                    st.error("規制によりブロックされました。マイルドな表現に変えてみてください。")
            except Exception as e:
                st.error(f"システムエラー: {e}")

st.markdown("---")
st.caption("© 2026 Karinto Group - Identity Lock V2")
