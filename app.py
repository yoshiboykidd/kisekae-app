import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import base64

# --- API設定 ---
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

st.set_page_config(layout="wide", page_title="AI KISEKAE Manager Ultra")

# --- UIデザイン ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stButton>button { 
        background: linear-gradient(45deg, #FF4B4B, #FF8F8F); 
        color: white; border: none; height: 3.5em; font-weight: bold; width: 100%; border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 AI KISEKAE Manager [Goldilocks Framing]")

col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("⚙️ 生成設定")
    source_img = st.file_uploader("1. 元写真をアップロード", type=['png', 'jpg', 'jpeg'])
    
    cloth = st.selectbox("2. 服装を選ぶ", 
        ["清楚な白ワンピース", "タイトな赤いドレス", "ナース服", "OL風オフィスカジュアル", 
         "紺色の学生服", "リゾート用スイムウェア（パレオ付き）", 
         "黒いレオタードとうさ耳カチューシャのコスチューム", 
         "和装（浴浴衣）", "メイド服"])
    
    bg = st.selectbox("3. 背景を選ぶ", 
        ["高級ホテルのスイートルーム", "夜の繁華街", "撮影スタジオ", "リゾートビーチ", "落ち着いたカフェ"])

    st.divider()
    run_button = st.button("✨ 黄金バランスで生成を開始")

with col_right:
    st.subheader("🖼️ 生成結果")
    if run_button and source_img:
        with st.spinner("バランス良く描画しています..."):
            try:
                # 【自然な余白を持たせた黄金バランスプロンプト】
                prompt = (
                    f"IMAGE EDITING TASK: Change the clothes and background while keeping the person's face. "
                    # --- 構図：適度な余白のある全身 ---
                    f"COMPOSITION: A well-balanced full body shot with a natural, comfortable margin around the woman. "
                    f"She should occupy about 80-85% of the frame height, leaving some breathable empty space above her head and below her feet. "
                    f"Ensure the entire figure from head to toe is visible and centered without feeling cramped. "
                    # --- 衣装と背景ボケ ---
                    f"NEW OUTFIT: A high-quality full-body outfit of {cloth}. "
                    f"NEW BACKGROUND: {bg} with intense f/1.2 soft bokeh blur. "
                    # --- 口元封鎖と顔の維持 ---
                    f"MOUTH: LIPS ARE FIRMLY PRESSED TOGETHER. NO TEETH VISIBLE. "
                    f"FACE PRESERVATION: Keep the exact facial features and identity of the Japanese woman in the reference. "
                    f"EXPRESSION: Calm and neutral. "
                    f"QUALITY: Photorealistic, 8k, professional studio lighting, masterpiece."
                )

                safety_settings = [
                    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROIT_CONTENT', threshold='BLOCK_NONE'),
                ]

                # 生成実行 (縦長 2:3 比率を維持)
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=[types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg'), prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        safety_settings=safety_settings,
                        image_config=types.ImageConfig(aspect_ratio="2:3")
                    )
                )

                if response.candidates and response.candidates[0].content.parts:
                    img_data = None
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            img_data = part.inline_data.data
                            break
                    
                    if img_data:
                        generated_img = Image.open(io.BytesIO(img_data))
                        final_img = generated_img.resize((600, 900))
                        
                        buffered = io.BytesIO()
                        final_img.save(buffered, format="JPEG", quality=95)
                        
                        # 画像の表示と保存
                        st.image(final_img, use_container_width=True)
                        st.download_button(
                            label="💾 全身画像を保存する",
                            data=buffered.getvalue(),
                            file_name="kisekae_balanced_full.jpg
