import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import base64

# --- API設定 ---
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

st.set_page_config(layout="wide", page_title="AI KISEKAE Tight-Portrait")

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

st.title("📸 AI KISEKAE Manager [Tight & High-Res]")

col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("⚙️ 生成設定")
    source_img = st.file_uploader("1. 元写真をアップロード", type=['png', 'jpg', 'jpeg'])
    
    cloth = st.selectbox("2. 服装を選ぶ", 
        ["清楚な白ワンピース", "タイトな赤いドレス", "OL風オフィスカジュアル", 
         "ナース服", "黒のレースクイーン", "リゾート用スイムウェア（パレオ付き）", 
         "黒いレオタードとうさ耳カチューシャのコスチューム", 
         "和装（浴衣）", "メイド服"])
    
    bg = st.selectbox("3. 背景を選ぶ", 
        ["高級ホテルのスイートルーム", "夜の繁華街", "撮影スタジオ", "リゾートビーチ", "落ち着いたカフェ"])

    st.divider()
    run_button = st.button("✨ 人物を大きく生成")

with col_right:
    st.subheader("🖼️ 生成結果")
    if run_button and source_img:
        with st.spinner("余白を削り、人物を大きく描画中..."):
            try:
                # 【余白を最小化し、人物を大きく配置するプロンプト】
                prompt = (
                    f"IMAGE EDITING TASK: Change the clothes and background while keeping the person's face. "
                    # --- 構図：余白なしの超寄り腰上 ---
                    f"COMPOSITION (CRITICAL): A VERY TIGHT waist-up portrait. The woman should fill almost the ENTIRE vertical height of the frame. "
                    f"Minimal empty space above the head. Zoom in so the subject is large and impactful. "
                    # --- 被写体のシャープ化 ---
                    f"FOCUS: Razor-sharp focus on the subject. Crisp details on eyes and skin. "
                    f"NEW BACKGROUND: {bg} with smooth, heavy bokeh background blur. "
                    # --- 同一性・口元・表情 ---
                    f"MOUTH: LIPS ARE FIRMLY PRESSED TOGETHER. NO TEETH VISIBLE. "
                    f"FACE: Keep the exact facial features and identity of the Japanese woman in the reference. "
                    f"QUALITY: Photorealistic photography, 8k, detailed skin texture, professional lighting, masterpiece."
                )

                safety_settings = [
                    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
                ]

                # 寄り構図に最適な 3:4 比率
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=[types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg'), prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        safety_settings=safety_settings,
                        image_config=types.ImageConfig(aspect_ratio="3:4")
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
                        final_img = generated_img.resize((600, 800))
                        
                        buffered = io.BytesIO()
                        final_img.save(buffered, format="JPEG", quality=95)
                        
                        st.image(final_img, use_container_width=True)
                        st.download_button(
                            label="💾 高画質画像を保存する",
                            data=buffered.getvalue(),
                            file_name="kisekae_tight.jpg",
                            mime="image/jpeg"
                        )
                    else:
                        st.warning("生成に失敗しました。")
                else:
                    st.error("安全フィルターによりブロックされました。")
