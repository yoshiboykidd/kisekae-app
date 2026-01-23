import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義 ---
VERSION = "1.6"
FLAT_LAY_PROMPT_BASE = (
    "Professional flat lay photography of a standalone clothing item. "
    "Top-down bird's eye view, centered on a solid pristine white background. "
    "Soft studio lighting, 8k high resolution, realistic fabric textures. "
    "STRICT RULE: No humans, no body parts, no mannequins. Apparel only."
)

def show_flatlay_ui():
    st.title(f"👕 衣装制作君 (v{VERSION})")
    st.info("解析は『Gemini 2.0 Flash』、生成は専用の『Image Generation』モデルで分担実行します。")

    # --- 2. APIクライアントの初期化 ---
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    # UIレイアウト
    with st.sidebar:
        st.header("📸 抽出設定")
        uploaded_file = st.file_uploader("衣装の参照画像をアップロード", type=['jpg', 'png', 'jpeg'], key="flat_up")
        
        category = st.selectbox("アイテムの種類", [
            "Casual fashion", "Night-fashion", "Satin slip", "Silk camisole", "Business suit", "Swimwear"
        ])
        
        st.divider()
        generate_btn = st.button("✨ 平置き画像を生成", type="primary")

    if uploaded_file:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. 元画像（解析対象）")
            st.image(uploaded_file, use_container_width=True)

        if generate_btn:
            with col2:
                st.subheader("2. 生成された衣装アンカー")
                
                with st.spinner("2.0 Flashが衣装を分析し、Image Genが描画中..."):
                    
                    input_img_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type='image/jpeg')
                    
                    try:
                        # --- Step 1: 解析 (分析のプロ: Gemini 2.0 Flashを使用) ---
                        analysis_prompt = (
                            f"Identify the {category} in this image. "
                            "Strictly describe: color, fabric texture, and details. "
                            "Ignore the person and background."
                        )
                        
                        analysis_res = client.models.generate_content(
                            model='gemini-2.0-flash', 
                            contents=[analysis_prompt, input_img_part]
                        )
                        clothing_desc = analysis_res.text

                        # --- Step 2: 生成 (画像出力のプロ: gemini-2.0-flash-exp-image-generationを使用) ---
                        # v1.6修正: 画像生成に特化した専用モデルへ切り替え
                        final_gen_prompt = f"{FLAT_LAY_PROMPT_BASE} \nDetails: {clothing_desc}"
                        
                        gen_response = client.models.generate_content(
                            model='gemini-2.0-flash-exp-image-generation', 
                            contents=[final_gen_prompt],
                            config=types.GenerateContentConfig(
                                response_modalities=['IMAGE'],
                                safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')],
                                image_config=types.ImageConfig(aspect_ratio="2:3")
                            )
                        )

                        if gen_response.candidates and gen_response.candidates[0].content.parts:
                            img_data = gen_response.candidates[0].content.parts[0].inline_data.data
                            final_img = Image.open(io.BytesIO(img_data))
                            st.image(final_img, use_container_width=True)
                            
                            buf = io.BytesIO()
                            final_img.save(buf, format="PNG")
                            st.download_button("📥 衣装アンカーを保存", buf.getvalue(), f"flat_{int(time.time())}.png", "image/png")
                        else:
                            st.warning("画像生成モデルからの応答が空です。")

                    except Exception as e:
                        st.error(f"エラー発生 (v1.6): {str(e)}")
    else:
        st.write("サイドバーから画像をアップロードしてください。")
