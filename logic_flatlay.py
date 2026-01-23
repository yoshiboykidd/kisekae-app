import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

def show_flatlay_ui():
    st.header("👕 平置き衣裳設計図 生成ツール")
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    with st.sidebar:
        ref = st.file_uploader("元の画像", type=['png', 'jpg', 'jpeg'])
        desc = st.text_input("特徴", "サテンの光沢")
        run = st.button("🚀 アンカーを生成")

    if run and ref:
        with st.spinner("生成中..."):
            prompt = f"Studio product flat lay of {desc}. High-end textile quality, neutral background."
            contents = [types.Part.from_bytes(data=ref.getvalue(), mime_type='image/jpeg')]
            response = client.models.generate_content(
                model='gemini-3-pro-image-preview',
                contents=contents + [prompt],
                config=types.GenerateContentConfig(response_modalities=['IMAGE'])
            )
            if response.candidates and response.candidates[0].content.parts:
                img = Image.open(io.BytesIO(response.candidates[0].content.parts[0].inline_data.data))
                st.image(img, use_container_width=True)
