import streamlit as st
from google import genai
import io
from PIL import Image

# --- ver 2.76: Flatlay Anchor Utility ---
def show_flatlay_ui():
    st.header("👕 平置き衣裳設計図 生成ツール")
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    with st.sidebar:
        ref = st.file_uploader("元の画像", type=['png', 'jpg', 'jpeg'], key="f_src")
        desc = st.text_input("衣裳の特徴", "サテン、シルクの質感", key="f_desc")
        run = st.button("🚀 アンカーを生成", type="primary")

    if run and ref:
        with st.spinner("アンカー生成中..."):
            try:
                # クラス名を使わず辞書で渡す
                config_dict = {
                    'response_modalities': ['IMAGE'],
                    'image_generation_config': {'aspect_ratio': '1:1'}
                }
                
                from google.genai import types
                contents = [types.Part.from_bytes(data=ref.getvalue(), mime_type='image/jpeg')]
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=contents + [f"Studio product flat lay of {desc}. Textile scan quality."],
                    config=config_dict
                )
                
                if response.candidates and response.candidates[0].content.parts:
                    img = Image.open(io.BytesIO(response.candidates[0].content.parts[0].inline_data.data))
                    st.image(img, use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    st.download_button("💾 アンカーを保存", buf.getvalue(), "anchor.png", "image/png")
            except Exception as e:
                st.error(f"エラー: {e}")
