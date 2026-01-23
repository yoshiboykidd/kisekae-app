import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義（検閲回避と高品質化のための黄金律） ---
FLAT_LAY_PROMPT_BASE = (
    "Professional flat lay photography of apparel, top-down view, "
    "organized neatly on a clean neutral background, soft natural studio lighting, 8k resolution. "
    "NO humans, NO body parts, NO faces. Just the clothing item itself."
)

def show_flatlay_ui():
    st.title("👕 衣装アンカー（平置き）生成ツール")
    st.info("人物写真から衣装のみを抽出し、KISEKAE用の「衣装設計図（平置き画像）」を生成します。")

    # APIクライアントの初期化
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    # UIレイアウト
    with st.sidebar:
        st.header("📸 抽出設定")
        uploaded_file = st.file_uploader("衣装の参照画像をアップロード", type=['jpg', 'png', 'jpeg'], key="flat_up")
        
        # 衣服カテゴリー（AI KISEKAEの定義に準拠）
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
                    # Step 1: 画像から衣服の詳細な特徴（素材、柄、形状）を言語化
                    # 人物の体型やポーズの情報を「捨てる」ための重要なステップ
                    analysis_prompt = (
                        f"Analyze the {category} in this image. "
                        "Focus strictly on apparel details: exact color, fabric texture, patterns, "
                        "neckline shape, and sleeve length. "
                        "Exclude all mentions of the person, pose, or body shape. "
                        "Output only a detailed description for image generation."
                    )
                    
                    input_img_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type='image/jpeg')
                    
                    try:
                        # 衣服の解析（Gemini 1.5 Flashを使用）
                        analysis_res = client.models.generate_content(
                            model='gemini-1.5-flash',
                            contents=[analysis_prompt, input_img_part]
                        )
                        clothing_desc = analysis_res.text

                        # Step 2: 解析結果を元に平置き画像を生成
                        final_gen_prompt = f"{FLAT_LAY_PROMPT_BASE} \nItem details: {clothing_desc}"
                        
                        # 画像生成（Gemini 3 Pro / Imagen 3 系のモデルを使用）
                        gen_response = client.models.generate_content(
                            model='gemini-3-pro-image-preview',
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
                            
                            # プレビュー表示
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
                            st.error("画像の生成に失敗しました（セーフティフィルタ等の影響）")

                    except Exception as e:
                        st.error(f"エラーが発生しました: {str(e)}")
    else:
        st.write("サイドバーから画像をアップロードしてください。")
