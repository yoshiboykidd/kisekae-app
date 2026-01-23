import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義 ---
VERSION = "1.9"
FLAT_LAY_PROMPT_BASE = (
    "A professional flat lay photograph of a standalone clothing item. "
    "Top-down view, centered on a clean white background. "
    "High-end studio lighting, 8k resolution, photorealistic fabric texture. "
    "STRICT RULE: No humans, no mannequins, no accessories. Apparel only."
)

def show_flatlay_ui():
    st.title(f"👕 衣装制作君 (v{VERSION})")
    st.info("SDKの仕様変更に合わせ、Imagen 4.0 の設定項目を最適化しました。")

    # --- 2. APIクライアントの初期化 ---
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    with st.sidebar:
        st.header("📸 抽出設定")
        uploaded_file = st.file_uploader("衣装の参照画像をアップロード", type=['jpg', 'png', 'jpeg'], key="flat_up")
        category = st.selectbox("アイテムの種類", ["Casual fashion", "Night-fashion", "Satin slip", "Silk camisole", "Business suit", "Swimwear"])
        st.divider()
        generate_btn = st.button("✨ 平置き画像を生成", type="primary")

    if uploaded_file:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("1. 元画像")
            st.image(uploaded_file, use_container_width=True)

        if generate_btn:
            with col2:
                st.subheader("2. 生成された衣装アンカー")
                
                # --- Step 1: 解析 (Gemini 2.0 Flash) ---
                with st.spinner("Step 1: 衣服を解析中..."):
                    try:
                        input_img_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type='image/jpeg')
                        analysis_res = client.models.generate_content(
                            model='gemini-2.0-flash', 
                            contents=[f"Identify the {category} and describe its color/material.", input_img_part]
                        )
                        clothing_desc = analysis_res.text
                    except Exception as e:
                        st.error(f"解析エラー: {e}")
                        return

                # --- Step 2: 生成 (Imagen 4.0) ---
                with st.spinner("Step 2: 描画中..."):
                    final_gen_prompt = f"{FLAT_LAY_PROMPT_BASE} \nDetails: {clothing_desc}"
                    
                    try:
                        # v1.9修正: エラーの原因となっていた safety_settings を削除し、
                        # GenerateImageConfig の引数を最小限（許可されているもののみ）に変更
                        # 
                        gen_response = client.models.generate_image(
                            model='imagen-4.0-generate-001',
                            prompt=final_gen_prompt,
                            config=types.GenerateImageConfig(
                                aspect_ratio="2:3",
                                output_mime_type='image/png'
                            )
                        )

                        if gen_response.generated_images:
                            img_bytes = gen_response.generated_images[0].image.image_bytes
                            final_img = Image.open(io.BytesIO(img_bytes))
                            st.image(final_img, use_container_width=True)
                            st.download_button("📥 保存", img_bytes, f"flat_{int(time.time())}.png", "image/png")
                        else:
                            st.error("モデルから画像が返されませんでした。")

                    except Exception as e:
                        # ここでエラーが出る場合は、さらに config 自体を None にして試す必要があります
                        st.error(f"生成エラー (v1.9): {str(e)}")
    else:
        st.write("サイドバーから画像をアップロードしてください。")
