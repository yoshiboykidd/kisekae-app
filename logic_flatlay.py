import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- ver 2.75: Flatlay Anchor Utility ---
def show_flatlay_ui():
    st.header("👕 平置き衣裳設計図 生成ツール")
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    with st.sidebar:
        ref = st.file_uploader("元の画像", type=['png', 'jpg', 'jpeg'], key="flat_src")
        desc = st.text_input("衣裳の特徴", "サテン、シルクの質感", key="flat_desc")
        run = st.button("🚀 アンカーを生成", type="primary")

    if run and ref:
        with st.spinner("アンカー生成中..."):
            prompt = f"Studio product flat lay of {desc}. High-end textile scan quality, neutral grey background, 8k."
            contents = [types.Part.from_bytes(data=ref.getvalue(), mime_type='image/jpeg')]
            try:
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=contents + [prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        image_generation_config=types.ImageGenerationConfig(aspect_ratio="1:1")
                    )
                )
                if response.candidates and response.candidates[0].content.parts:
                    img = Image.open(io.BytesIO(response.candidates[0].content.parts[0].inline_data.data))
                    st.image(img, caption="生成されたアンカー画像", use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    st.download_button("💾 アンカーを保存", buf.getvalue(), "new_anchor.png", "image/png")
                else:
                    st.error("アンカー生成に失敗しました。")
            except Exception as e:
                st.error(f"エラー: {e}")
