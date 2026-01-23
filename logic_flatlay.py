import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義（プロフェッショナルな平置き写真のための黄金律） ---
FLAT_LAY_PROMPT_BASE = (
    "Professional flat lay photography of apparel, captured from a direct top-down bird's eye view. "
    "The clothing is organized neatly on a clean, solid white studio background. "
    "Soft, even natural studio lighting with minimal shadows. 8k high-definition texture. "
    "STRICT RULE: No humans, no mannequins, no body parts, no faces. "
    "Only the standalone clothing item itself."
)

def show_flatlay_ui():
    st.title("👕 衣装制作君（衣装アンカー生成）")
    st.info("人物写真から衣装のみを抽出し、KISEKAE用の「衣装設計図（平置き画像）」を生成します。")

    # APIクライアントの初期化（最新の google-genai SDK 準拠）
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    # UIレイアウト
    with st.sidebar:
        st.header("📸 抽出設定")
        uploaded_file = st.file_uploader("衣装の参照画像をアップロード", type=['jpg', 'png', 'jpeg'], key="flat_up")
        
        category = st.selectbox("アイテムの種類", [
            "Casual fashion", "Night-fashion", "Satin slip", "Silk camisole", "Business suit", "Swimwear"
        ])
        
        generate_btn = st.button("✨ 平置き画像を生成", type="primary")

    if uploaded_file:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. 元画像（解析対象）")
            st.image(uploaded_file, use_container_width=True)

        if generate_btn:
            with col2:
                st.subheader("2. 生成された衣装アンカー")
                
                with st.spinner("Geminiが衣装を解析・再構築中..."):
                    # --- Step 1: 衣装の詳細を言語化（Gemini 1.5 Flashを使用） ---
                    analysis_prompt = (
                        f"Identify and analyze the {category} in this image. "
                        "Describe the garment strictly: exact color, fabric material (satin, cotton, silk, etc.), "
                        "patterns, collar shape, buttons, and sleeve details. "
                        "Ignore the person, their pose, and the background. "
                        "Output only the detailed physical description of the garment."
                    )
                    
                    input_img_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type='image/jpeg')
                    
                    try:
                        # 解析実行
                        analysis_res = client.models.generate_content(
                            model='gemini-1.5-flash',
                            contents=[analysis_prompt, input_img_part]
                        )
                        clothing_desc = analysis_res.text

                        # --- Step 2: 平置き画像を生成（Imagen 3を使用） ---
                        final_gen_prompt = f"{FLAT_LAY_PROMPT_BASE} \nClothing details: {clothing_desc}"
                        
                        gen_response = client.models.generate_content(
                            model='imagen-3.0-generate-001', # 404エラーを防ぐ最新の指定方法
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
                            
                            # ダウンロードボタン
                            buf = io.BytesIO()
                            final_img.save(buf, format="PNG")
                            st.download_button(
                                label="📥 衣装アンカーを保存（IMAGE 2用）",
                                data=buf.getvalue(),
                                file_name=f"flat_anchor_{int(time.time())}.png",
                                mime="image/png"
                            )
                        else:
                            st.warning("画像の生成に失敗しました。プロンプトや安全設定を確認してください。")

                    except Exception as e:
                        st.error(f"システムエラーが発生しました: {str(e)}")
                        st.info("requirements.txtが更新され、AppがRebootされているか確認してください。")
    else:
        st.write("サイドバーから画像をアップロードしてください。")
