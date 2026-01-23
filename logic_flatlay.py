import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義 (v2.1修正: より写真的な質感と背景の純粋さを強化) ---
VERSION = "2.1"
FLAT_LAY_PROMPT_BASE = (
    "A commercial-grade fashion product photograph. Direct top-down flat lay view. "
    "The garment is centered on a seamless, professional pure white studio background (#FFFFFF). "
    "Even, high-key studio lighting that eliminates harsh shadows and highlights every texture. "
    "8k macro photography, extremely detailed fabric weave, photorealistic materials. "
    "STRICT RULE: No human figures, no skin, no mannequins, no accessories. "
    "Only the standalone clothing item, laid perfectly flat."
)

def show_flatlay_ui():
    st.title(f"👕 衣装制作君 (v{VERSION})")
    st.info("解析の『言語化精度』を強化し、元の衣装の素材感・細部をImagen 4.0へ強力に伝達します。")

    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    with st.sidebar:
        st.header("📸 抽出設定")
        uploaded_file = st.file_uploader("衣装の参照画像をアップロード", type=['jpg', 'png', 'jpeg'], key="flat_up")
        category = st.selectbox("アイテムの種類", ["Casual fashion", "Night-fashion", "Satin slip", "Silk camisole", "Business suit", "Swimwear"])
        st.divider()
        generate_btn = st.button("✨ 精密生成を実行", type="primary")

    if uploaded_file:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("1. 元画像")
            st.image(uploaded_file, use_container_width=True)

        if generate_btn:
            with col2:
                st.subheader("2. 生成された衣装アンカー")
                
                # --- Step 1: 解析 (v2.1修正: 『技術仕様書』レベルの言語化を要求) ---
                with st.spinner("Step 1: 衣服の素材・構造を精密スキャン中..."):
                    try:
                        input_img_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type='image/jpeg')
                        
                        # AIに対して、単なる説明ではなく「設計図」を書かせるようにプロンプトを強化
                        analysis_prompt = (
                            f"Analyze the {category} in the provided image as a textile expert. "
                            "Examine and describe: 1. Exact color hex-code style, 2. Fabric texture (e.g., luster of satin, weave of lace, transparency), "
                            "3. Detailed silhouette (neckline, sleeve length, hemline), 4. Any specific patterns or embellishments. "
                            "Output a highly technical specification of the garment only. Do not mention the human."
                        )
                        
                        analysis_res = client.models.generate_content(
                            model='gemini-2.0-flash', 
                            contents=[analysis_prompt, input_img_part]
                        )
                        clothing_desc = analysis_res.text
                        
                        # どのような解析結果になったかユーザーにチラ見せする（デバッグ用）
                        with st.expander("AIの解析レポート（抽出された特徴）"):
                            st.write(clothing_desc)

                    except Exception as e:
                        st.error(f"解析エラー: {e}")
                        return

                # --- Step 2: 生成 (Imagen 4.0) ---
                with st.spinner("Step 2: Imagen 4.0 で再構築中..."):
                    final_gen_prompt = f"{FLAT_LAY_PROMPT_BASE} \nTechnical Specs: {clothing_desc}"
                    
                    try:
                        gen_response = client.models.generate_image(
                            model='imagen-4.0-generate-001',
                            prompt=final_gen_prompt,
                            config=types.GenerateImageConfig(
                                aspect_ratio="3:4",
                                output_mime_type='image/png'
                            )
                        )

                        if gen_response.generated_images:
                            img_bytes = gen_response.generated_images[0].image.image_bytes
                            final_img = Image.open(io.BytesIO(img_bytes))
                            st.image(final_img, use_container_width=True)
                            st.download_button("📥 高精度アンカーを保存", img_bytes, f"flat_{int(time.time())}.png", "image/png")
                        else:
                            st.error("モデルから画像が返されませんでした。")

                    except Exception as e:
                        st.error(f"生成エラー (v2.1): {str(e)}")
    else:
        st.write("サイドバーから画像をアップロードしてください。")
