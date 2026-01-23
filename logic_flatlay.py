import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義 ---
VERSION = "1.7"
FLAT_LAY_PROMPT_BASE = (
    "A professional flat lay photograph of a standalone clothing item. "
    "Bird's eye view, perfectly centered on a clean white background. "
    "High-end studio lighting, 8k resolution, visible fabric texture. "
    "STRICT RULE: Only the clothing. No humans, no mannequins, no accessories."
)

def show_flatlay_ui():
    st.title(f"👕 衣装制作君 (v{VERSION})")
    st.info("解析（Gemini 2.0）と描画（Imagen 4.0）の『完全分業制』に移行しました。")

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
                
                with st.spinner("Step 1: Gemini 2.0 が衣装を解析中..."):
                    
                    input_img_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type='image/jpeg')
                    
                    try:
                        # --- Step 1: 解析 (会話モデル: Gemini 2.0 Flash) ---
                        analysis_prompt = (
                            f"Identify the {category} in this image. "
                            "Describe only the garment: color, material, and patterns. "
                            "Output a concise prompt for image generation."
                        )
                        
                        analysis_res = client.models.generate_content(
                            model='gemini-2.0-flash', 
                            contents=[analysis_prompt, input_img_part]
                        )
                        clothing_desc = analysis_res.text

                        with st.spinner("Step 2: Imagen 4.0 が高精度描画中..."):
                            # --- Step 2: 生成 (画像専用モデル: Imagen 4.0) ---
                            # v1.7修正: generate_content ではなく generate_image を使用
                            final_gen_prompt = f"{FLAT_LAY_PROMPT_BASE} \nDetails: {clothing_desc}"
                            
                            # 
                            gen_response = client.models.generate_image(
                                model='imagen-4.0-generate-001', 
                                prompt=final_gen_prompt,
                                config=types.GenerateImageConfig(
                                    aspect_ratio="2:3",
                                    safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')],
                                    output_mime_type='image/png'
                                )
                            )

                            if gen_response.generated_images:
                                # v1.7修正: generate_image の戻り値形式に合わせて取得
                                img_bytes = gen_response.generated_images[0].image.image_bytes
                                final_img = Image.open(io.BytesIO(img_bytes))
                                st.image(final_img, use_container_width=True)
                                
                                st.download_button("📥 衣装アンカーを保存", img_bytes, f"flat_{int(time.time())}.png", "image/png")
                            else:
                                st.warning("Imagen 4.0 から画像が返されませんでした。")

                    except Exception as e:
                        st.error(f"エラー発生 (v1.7): {str(e)}")
                        st.info("APIの呼び出しメソッドを最新の画像専用方式に切り替えました。")
    else:
        st.write("サイドバーから画像をアップロードしてください。")
