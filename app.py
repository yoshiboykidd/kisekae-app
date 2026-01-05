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

st.title("📸 AI KISEKAE Manager [Full Body & Safety Fixed]")

col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("⚙️ 生成設定")
    source_img = st.file_uploader("1. 元写真をアップロード", type=['png', 'jpg', 'jpeg'])
    
    # ビキニの名称を変更して安全性を高める
    cloth = st.selectbox("2. 服装を選ぶ", 
        ["清楚な白ワンピース", "タイトな赤いドレス", "ナース服", "OL風オフィスカジュアル", 
         "紺色の学生服", "リゾート用スイムウェア（パレオ付き）", 
         "黒いレオタードとうさ耳カチューシャのコスチューム", 
         "和装（浴衣）", "メイド服"])
    
    bg = st.selectbox("3. 背景を選ぶ", 
        ["高級ホテルのスイートルーム", "夜の繁華街", "撮影スタジオ", "リゾートビーチ", "落ち着いたカフェ"])

    st.divider()
    run_button = st.button("✨ 全身写真で生成を開始")

with col_right:
    st.subheader("🖼️ 生成結果")
    if run_button and source_img:
        with st.spinner("全身構図で描画中..."):
            try:
                # 【全身指定(広角)＋着せ替え＋口元封鎖プロンプト】
                prompt = (
                    f"IMAGE EDITING TASK: Change the clothes and background while keeping the person's face. "
                    # --- 1. 構図（最優先・広角全身） ---
                    f"COMPOSITION (CRITICAL): WIDE-ANGLE FULL BODY SHOT. Standing pose. The entire physique from head to feet must be clearly visible in the frame. "
                    # --- 2. 新しい衣装と背景 ---
                    f"NEW OUTFIT: A high-quality full-body outfit of {cloth}. "
                    f"NEW BACKGROUND: {bg} with intense f/1.2 soft bokeh blur. "
                    # --- 3. 口元と歯の物理的封鎖 (継続) ---
                    f"MOUTH: LIPS MUST BE FIRMLY SEALED TOGETHER. NO TEETH VISIBLE anywhere. "
                    # --- 4. 顔の維持 ---
                    f"FACE PRESERVATION: Keep the facial features and identity of the Japanese woman in the reference. "
                    f"EXPRESSION: Calm and neutral. "
                    f"QUALITY: Photorealistic, 8k, professional studio lighting, masterpiece. "
                )

                safety_settings = [
                    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
                ]

                # アスペクト比をさらに縦長(2:3)に変更して全身を促す
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
                        # リサイズも縦長に合わせて調整（横幅基準600px）
                        final_img = generated_img.resize((600, 900))
                        
                        buffered = io.BytesIO()
                        final_img.save(buffered, format="JPEG", quality=95)
                        img_base64 = base64.b64encode(buffered.getvalue()).decode()
                        
                        st.markdown(f'<img src="data:image/jpeg;base64,{img_base64}" width="100%" style="border-radius:10px;">', unsafe_allow_html=True)
                        st.download_button("💾 全身画像を保存",
