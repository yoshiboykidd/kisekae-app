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

    st.title("📸 AI KISEKAE [Ultimate Identity V3]")

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        # ラベルで重要性を強調
        src_img = st.file_uploader("1. キャスト写真 (【最重要】顔の生体データ源)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装写真 (柄・色の見本)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル", ["サマー・リゾートウェア", "タイトミニドレス", "ワンピースドレス", "ナースウェア", "メイドウェア", "浴衣"])
        cloth_detail = st.text_input("追加指示", placeholder="例：黒サテン地、ピンクのリボン")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "サマー・リゾート地"])
        st.divider()
        run_button = st.button("✨ 生体認証レベルで生成")

    if run_button and src_img:
        st.subheader("🖼️ 生成結果")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        base_parts = [types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # AIへの最終通告プロンプト
        # "Biometric Match"（生体認証的一致）という強い言葉を使用
        prompt = (
            f"CRITICAL OPERATION: BIOMETRIC IDENTITY TRANSFER.\n"
            f"SOURCE 1 (IDENTITY): The person in IMAGE 1. The final images MUST be a PERFECT BIOMETRIC MATCH to this person's exact facial structure, eyes, nose, and mouth. It is NOT a 'similar' person; it is the EXACT SAME person.\n"
            f"SOURCE 2 (STYLE DNA): IMAGE 2 is ONLY used for fabric patterns and colors. DO NOT blend the face from IMAGE 2.\n"
            f"TASK: Create a 2x2 grid photograph.\n"
            f"OUTFIT: A {cloth_main} featuring the exact textile pattern and color palette from SOURCE 2. {cloth_detail}.\n"
            f"POSES: [TL: Standing Front], [TR: Walking Side], [BL: Sitting], [BR: Close-up Portrait].\n"
            f"MANDATORY RULES: Lips sealed (no teeth). Skin texture must be preserved from IMAGE 1.\n"
            f"QUALITY: 8k photorealistic studio portrait. Background: {bg}."
        )

        with st.spinner("生体データを解析し、超高精度生成中..."):
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
st.caption("© 2026 Karinto Group - Ultimate Identity V3")
