import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義 ---
VERSION = "1.4"
# v1.4修正: 最新のImagen 4.0に最適化した高品質プロンプト
FLAT_LAY_PROMPT_BASE = (
    "Masterpiece, professional flat lay photography of a standalone clothing item. "
    "Top-down bird's eye view, centered composition on a solid minimalist white background. "
    "Ultra-high resolution 8k texture, realistic fabric folds, soft studio lighting. "
    "STRICT RULE: No humans, no body parts, no mannequins. Pure apparel only."
)

def show_flatlay_ui():
    st.title(f"👕 衣装制作君 (v{VERSION})")
    st.info("2026年最新モデル（Gemini 2.0 & Imagen 4.0）を使用して、最高精度の衣装アンカーを生成します。")

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
        
        # 診断ツール（念のため残しておきます）
        with st.expander("🛠 診断ツール"):
            if st.button("利用可能なモデルを再リストアップ"):
                try:
                    for m in client.models.list():
                        st.code(m.name)
                except Exception as e:
                    st.error(f"エラー: {e}")

    if uploaded_file:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. 元画像（解析対象）")
            st.image(uploaded_file, use_container_width=True)

        if generate_btn:
            with col2:
                st.subheader("2. 生成された衣装アンカー")
                
                with st.spinner("Gemini 2.0 が衣装を精密解析中..."):
                    # --- Step 1: 解析 (v1.4修正: 利用可能な gemini-2.0-flash を使用) ---
                    analysis_prompt = (
                        f"Identify and analyze the {category} in this image. "
                        "Describe the garment strictly: color, material texture, and silhouette. "
                        "Focus on details for high-fidelity reconstruction."
                    )
                    
                    input_img_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type='image/jpeg')
                    
                    try:
                        # 解析実行
                        analysis_res = client.models.generate_content(
                            model='gemini-2.0-flash', 
                            contents=[analysis_prompt, input_img_part]
                        )
                        clothing_desc = analysis_res.text

                        # --- Step 2: 生成 (v1.4修正: 利用可能な imagen-4.0-generate-001 を使用) ---
                        final_gen_prompt = f"{FLAT_LAY_PROMPT_BASE} \nDetails: {clothing_desc}"
                        
                        gen_response = client.models.generate_content(
                            model='imagen-4.0-generate-001', 
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
                            st.warning("Imagen 4.0からの応答が空です。")

                    except Exception as e:
                        st.error(f"エラー発生 (v1.4): {str(e)}")
    else:
        st.write("サイドバーから画像をアップロードしてください。")
