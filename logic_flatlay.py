import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義 ---
VERSION = "1.3"
FLAT_LAY_PROMPT_BASE = (
    "Professional flat lay photography of apparel, captured from a direct top-down bird's eye view. "
    "The clothing is organized neatly on a clean, solid white studio background. "
    "Soft, even natural studio lighting with minimal shadows. 8k high-definition texture. "
    "STRICT RULE: No humans, no mannequins, no body parts, no faces. "
    "Only the standalone clothing item itself."
)

def show_flatlay_ui():
    st.title(f"👕 衣装制作君 (v{VERSION})")
    st.info("写真から衣装のみを抽出し、KISEKAE用の「衣装設計図（平置き画像）」を生成します。")

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
        
        # --- v1.3 追加: 診断用ボタン ---
        st.subheader("🛠 診断ツール")
        if st.button("利用可能なモデルをリストアップ"):
            try:
                st.write("利用可能なモデル一覧:")
                for m in client.models.list():
                    st.code(m.name)
            except Exception as e:
                st.error(f"モデルリストの取得に失敗: {e}")

    if uploaded_file:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. 元画像（解析対象）")
            st.image(uploaded_file, use_container_width=True)

        if generate_btn:
            with col2:
                st.subheader("2. 生成された衣装アンカー")
                
                with st.spinner("Geminiが衣装を解析・再構築中..."):
                    # --- Step 1: 解析 (v1.3修正: エイリアスではなく詳細なバージョン名を指定) ---
                    analysis_prompt = (
                        f"Identify and analyze the {category} in this image. "
                        "Describe the garment strictly: color, fabric material, patterns, and shape. "
                        "Output only the detailed physical description."
                    )
                    
                    input_img_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type='image/jpeg')
                    
                    try:
                        # gemini-1.5-flash-002 は多くの環境で安定して動作する指定方法です
                        analysis_res = client.models.generate_content(
                            model='gemini-1.5-flash-002', 
                            contents=[analysis_prompt, input_img_part]
                        )
                        clothing_desc = analysis_res.text

                        # --- Step 2: 生成 (v1.3修正: モデル名を再定義) ---
                        final_gen_prompt = f"{FLAT_LAY_PROMPT_BASE} \nClothing details: {clothing_desc}"
                        
                        gen_response = client.models.generate_content(
                            model='imagen-3.0-generate-001', 
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
                            st.warning("生成結果が空です。セーフティフィルタを確認してください。")

                    except Exception as e:
                        st.error(f"エラー発生 (v1.3): {str(e)}")
                        st.info("サイドバーの『利用可能なモデルをリストアップ』を押して、出力された名前を確認してください。")
    else:
        st.write("サイドバーから画像をアップロードしてください。")
