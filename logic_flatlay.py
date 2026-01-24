import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義 (v2.2: 商業写真クオリティの定義) ---
VERSION = "2.2"
FLAT_LAY_PROMPT_BASE = (
    "A high-end professional fashion catalog flat lay photography of a SINGLE standalone garment. "
    "Shot from a direct top-down bird's-eye view, perfectly centered on a seamless, solid pure white studio background (#FFFFFF). "
    "High-key studio lighting, no harsh shadows, extremely sharp focus. "
    "8k resolution, photorealistic fabric textures and intricate material details. "
    "STRICT RULE: Only the clothing. NO humans, NO body parts, NO mannequins, NO accessories."
)

def show_flatlay_ui():
    st.header(f"👕 洋服アンカー制作 (v{VERSION})")
    st.info("解析（Gemini 2.0）と描画（Imagen 4.0）の連携により、実物の『質感・構造』を精密に再現します。")
    
    # APIクライアントの初期化
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    # バイトデータ保持用の初期化
    if "flat_ref_bytes" not in st.session_state: 
        st.session_state.flat_ref_bytes = None

    with st.sidebar:
        st.header("📸 抽出設定")
        ref_img = st.file_uploader("元の衣装画像 (IMAGE 2の素)", type=['png', 'jpg', 'jpeg'], key="f_src")
        
        if ref_img:
            st.session_state.flat_ref_bytes = ref_img.getvalue()
            st.image(ref_img, caption="解析対象のプレビュー", use_container_width=True)
        
        category = st.selectbox("アイテムの種類", [
            "Casual fashion", "Night-fashion", "Satin slip", "Silk camisole", "Business suit", "Swimwear"
        ])
        
        st.divider()
        run_btn = st.button("🚀 アンカー（設計図）を精密生成", type="primary")

    if run_btn and st.session_state.flat_ref_bytes:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. AI解析結果")
            # --- Step 1: 解析 (Gemini 2.0 Flash) ---
            with st.spinner("テキスタイル・スキャンを実行中..."):
                try:
                    input_img_part = types.Part.from_bytes(
                        data=st.session_state.flat_ref_bytes, 
                        mime_type='image/jpeg'
                    )
                    
                    # 衣服の「仕様書」を書かせるためのプロンプト
                    analysis_prompt = (
                        f"Analyze the {category} in this image as a textile and fashion expert. "
                        "Precisely describe the following for image reconstruction: "
                        "1. Fabric material and finish (e.g., glossy satin, sheer lace, matte cotton), "
                        "2. Exact color and lighting effects on the surface, "
                        "3. Structural details (neckline, stitching, hemline, silhouette). "
                        "Focus exclusively on the garment. Output a technical specification."
                    )
                    
                    analysis_res = client.models.generate_content(
                        model='gemini-2.0-flash', 
                        contents=[analysis_prompt, input_img_part]
                    )
                    clothing_desc = analysis_res.text
                    
                    st.success("✅ 衣服の特徴を完全に言語化しました")
                    with st.expander("AIのスキャンレポートを確認"):
                        st.write(clothing_desc)
                except Exception as e:
                    st.error(f"解析フェーズでエラーが発生しました: {e}")
                    return

        with col2:
            st.subheader("2. 完成したアンカー（IMAGE 2用）")
            # --- Step 2: 生成 (Imagen 4.0) ---
            with st.spinner("Imagen 4.0 が実物に近い質感を再構築中..."):
                final_gen_prompt = f"{FLAT_LAY_PROMPT_BASE} \nTechnical Specification: {clothing_desc}"
                
                try:
                    # 
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
                        
                        # ダウンロードボタン
                        st.download_button(
                            label="💾 アンカー画像を保存", 
                            data=img_bytes, 
                            file_name=f"clothing_anchor_{int(time.time())}.png", 
                            mime="image/png"
                        )
                    else:
                        st.error("画像生成エンジンから応答がありませんでした。")

                except Exception as e:
                    st.error(f"生成フェーズでエラーが発生しました (v{VERSION}): {str(e)}")
                    st.info("Imagen 4.0 の呼び出し制限またはアスペクト比設定を確認してください。")
    else:
        if not st.session_state.flat_ref_bytes:
            st.write("サイドバーから画像をアップロードし、生成ボタンを押してください。")
