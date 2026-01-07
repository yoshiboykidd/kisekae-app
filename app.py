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

    st.title("📸 AI KISEKAE [Absolute Identity Lock]")

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        src_img = st.file_uploader("1. キャスト写真 (顔・骨格：絶対遵守)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装素材写真 (柄・色：引用のみ)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. 強制スタイル (形)", [
            "リゾート・サマー・スタイル", 
            "タイトフィット・ミニドレス", 
            "モダン・フェミニン・ドレス", 
            "プロフェッショナル・ナース服", 
            "クラシック・メイド・スタイル",
            "サマー・ユカタ・スタイル"
        ])
        cloth_detail = st.text_input("追加指示", placeholder="例：黒サテン地、ピンクのリボン")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "サマー・リゾート地"])
        st.divider()
        run_button = st.button("✨ 掟を遵守して一括生成")

    if run_button and src_img:
        st.subheader("🖼️ 生成結果")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        base_parts = [types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # AIへの「絶対命令」プロンプト
        # IMAGE 1を唯一の「人物」として定義し、IMAGE 2を「テクスチャ」に貶める
        prompt = (
            f"SYSTEM COMMAND: You are a professional photographer. Follow these laws strictly.\n\n"
            f"LAW 1 (IDENTITY): The SUBJECT is the woman in IMAGE 1. Every single feature of her face, jawline, and eyes MUST be 100% identical to IMAGE 1. NEVER use the face or body from IMAGE 2.\n"
            f"LAW 2 (MOUTH): In all panels, the woman's LIPS MUST BE SEALED. NO TEETH ALLOWED. Failure to hide teeth is a critical error.\n"
            f"LAW 3 (OUTFIT): The garment shape MUST be '{cloth_main}'. Use IMAGE 2 ONLY as a texture/color pattern source. Ignore the person wearing the clothes in IMAGE 2.\n"
            f"LAW 4 (CONSISTENCY): Create a 2x2 grid. All 4 panels must show the SAME woman and SAME outfit but in different poses.\n\n"
            f"POSES IN GRID:\n"
            f"- Top-Left: Full body standing.\n"
            f"- Top-Right: Dynamic movement.\n"
            f"- Bottom-Left: Sitting gracefully.\n"
            f"- Bottom-Right: Face close-up.\n\n"
            f"OUTPUT: 8k photorealistic photography, professional lighting, sharp focus on the woman. Background: {bg}."
        )

        with st.spinner("掟に基づき、アイデンティティをロック中..."):
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
                    st.error("AI規制によりブロックされました。マイルドな指示に変えてみてください。")
            except Exception as e:
                st.error(f"エラー: {e}")

st.markdown("---")
st.caption("© 2026 Karinto Group - Absolute Identity Engine V6")
