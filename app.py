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

    st.title("📸 AI KISEKAE [Identity First]")

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        src_img = st.file_uploader("1. キャスト写真 (顔と体型の見本)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装写真 (柄と色の見本のみ)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル", ["リゾートウェア", "タイトドレス", "ワンピース", "ナース", "メイド", "浴衣"])
        cloth_detail = st.text_input("追加指示", placeholder="例：黒とピンク、リボン")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "ビーチ"])
        st.divider()
        run_button = st.button("✨ 4枚一括生成")

    if run_button and src_img:
        st.subheader("🖼️ 生成結果")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        base_parts = [types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # プロンプトを極限までシンプルに整理
        # 「誰を撮るか」と「何を着せるか」を明確に分離
        prompt = (
            f"PHOTO TASK: A 2x2 grid of the woman from IMAGE 1.\n"
            f"HUMAN: IDENTICAL to IMAGE 1 (Face, Bone structure, Body). IGNORE the person in IMAGE 2.\n"
            f"OUTFIT: A {cloth_main}. Use the EXACT colors and patterns from IMAGE 2. {cloth_detail}.\n"
            f"POSES: 4 different professional poses (Standing, Walking, Sitting, Close-up).\n"
            f"RULE: LIPS SEALED, NO TEETH. Sharp focus. Background: {bg}.\n"
            f"QUALITY: Photorealistic 8k, professional lighting."
        )

        with st.spinner("生成中..."):
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
                    
                    for i, coord in enumerate(coords):
                        with placeholders[i]:
                            cropped = full_img.crop(coord).resize((600, 900))
                            st.image(cropped, use_container_width=True)
                            buf = io.BytesIO()
                            cropped.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p{i+1}.jpg", mime="image/jpeg", key=f"btn_{i}")
                else:
                    st.error("規制によりブロックされました。マイルドな指示にしてください。")
            except Exception as e:
                st.error(f"エラー: {e}")

st.markdown("---")
st.caption("© 2026 Karinto Group - Simple Identity Engine")
