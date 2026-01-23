import streamlit as st
from google import genai
from google.genai import types
import io
from PIL import Image

# --- ver 2.80: Flatlay Anchor Utility (SDK 0.6.0 Update) ---
def show_flatlay_ui():
    st.header("👕 平置き衣裳設計図（アンカー）生成ツール")
    st.write("複雑な衣装を、KISEKAE Mainで読み取りやすい『綺麗な設計図』に変換します。")
    
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    with st.sidebar:
        ref = st.file_uploader("元の衣装画像", type=['png', 'jpg', 'jpeg'], key="f_src")
        desc = st.text_area("衣装の特徴（素材や柄）", "サテンの光沢、細かい刺繍、レースの質感など", key="f_desc")
        run = st.button("🚀 アンカー画像を生成", type="primary")

    if run and ref:
        with st.spinner("高品質なアンカーを生成中..."):
            try:
                # SDK 0.6.0 準拠の命令構築
                prompt = (
                    f"Professional studio catalog photography of a garment flat lay. "
                    f"Design: {desc}. Isolated perfectly on a neutral solid grey background. "
                    f"Industrial textile scan quality, 8k, extreme detail on fabric texture, "
                    f"soft even lighting, no shadows."
                )
                
                contents = [types.Part.from_bytes(data=ref.getvalue(), mime_type='image/jpeg')]
                
                # 画像設定のバリデーションを通過させる最新の書き方
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=contents + [prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        image_generation_config=types.ImageGenerationConfig(
                            aspect_ratio="1:1",  # 設計図は1:1が最も安定
                            number_of_images=1
                        )
                    )
                )
                
                if response.candidates and response.candidates[0].content.parts:
                    img_data = response.candidates[0].content.parts[0].inline_data.data
                    img = Image.open(io.BytesIO(img_data))
                    
                    st.success("✨ アンカー画像の生成に成功しました")
                    st.image(img, caption="生成されたアンカー（この画像を保存してMainで使用してください）", use_container_width=True)
                    
                    # ダウンロードボタン
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    st.download_button(
                        label="💾 このアンカー画像を保存",
                        data=buf.getvalue(),
                        file_name="anchor_blueprint.png",
                        mime="image/png"
                    )
                else:
                    st.error("生成結果が空でした。別の画像で試してください。")
                    
            except Exception as e:
                st.error(f"アンカー生成エラー: {e}")
