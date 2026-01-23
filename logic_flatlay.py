import streamlit as st
from google import genai
from google.genai import types
import io
from PIL import Image

def show_flatlay_ui():
    st.header("👕 平置き衣裳設計図 生成ツール")
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    with st.sidebar:
        ref = st.file_uploader("元の画像", type=['png', 'jpg', 'jpeg'], key="f_src")
        desc = st.text_input("特徴", "サテン、刺繍の質感", key="f_desc")
        run = st.button("🚀 アンカーを生成", type="primary")

    if run and ref:
        with st.spinner("アンカー生成中..."):
            try:
                contents = [types.Part.from_bytes(data=ref.getvalue(), mime_type='image/jpeg')]
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=contents + [f"Studio product flat lay of {desc}. Scan quality."],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        image_generation_config=types.ImageGenerationConfig(
                            aspect_ratio="1:1"
                        )
                    )
                )
                if response.candidates and response.candidates[0].content.parts:
                    img_data = response.candidates[0].content.parts[0].inline_data.data
                    img = Image.open(io.BytesIO(img_data))
                    st.image(img, use_container_width=True)
            except Exception as e:
                st.error(f"エラー: {e}")
