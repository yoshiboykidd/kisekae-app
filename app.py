import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import base64

# --- API設定 ---
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

st.set_page_config(layout="wide", page_title="AI KISEKAE Manager Gold")

# --- プロフェッショナルUIデザイン ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stButton>button { 
        background: linear-gradient(45deg, #FF4B4B, #FF8F8F); 
        color: white; border: none; height: 3.5em; font-weight: bold; width: 100%; border-radius: 10px;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 AI KISEKAE Manager [Gold Standard]")

col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("⚙️ 生成設定")
    source_img = st.file_uploader("1. 元写真をアップロード", type=['png', 'jpg', 'jpeg'])
    
    # 現場で使いやすい衣装ラインナップ
    cloth = st.selectbox("2. 服装を選ぶ", 
        ["清楚な白ワンピース", "タイトな赤いドレス", "OL風オフィスカジュアル", 
         "ナース服", "黒のレースクイーン", "リゾート用スイムウェア（パレオ付き）", 
         "黒いレオタードとうさ耳カチューシャのコスチューム", 
         "和装（浴衣）", "メイド服"])
    
    bg = st.selectbox("3. 背景を選ぶ", 
        ["高級ホテルのスイートルーム", "夜の繁華街", "撮影スタジオ", "リゾートビーチ", "落ち着いたカフェ"])

    st.divider()
    run_button = st.button("✨ 最高画質ポートレートを生成")

with col_right:
    st.subheader("🖼️ 生成結果")
    if run_button and source_img:
        with st.spinner("リアルな質感を再現中..."):
            try:
                # 【これまでの知見をすべて注ぎ込んだ黄金プロンプト】
                prompt = (
                    f"IMAGE EDITING TASK: Change the clothes and background while keeping the person's face. "
                    # --- 構図：質感重視の腰上 ---
                    f"COMPOSITION: A professional waist-up portrait. The subject is framed from head to waist. "
                    # --- 被写体のシャープ化とピント ---
                    f"FOCUS: Razor-sharp focus on the subject. The person is crisp and highly detailed. "
                    f"NEW BACKGROUND: {bg} with smooth, professional bokeh background blur. "
                    # --- 同一性・口元・表情 ---
                    f"MOUTH: LIPS ARE FIRMLY PRESSED TOGETHER. NO TEETH VISIBLE. "
                    f"FACE: Keep the exact facial features and identity of the Japanese woman in the reference image. "
                    f"EXPRESSION: Calm, neutral, and pleasant. "
                    # --- 質感とライティング ---
                    f"QUALITY: Photorealistic photography, 8k, detailed skin texture, sparkle in eyes, professional studio lighting, masterpiece."
                )

                safety_settings = [
                    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
                ]

                # ポートレートに最適な 3:4 比率
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=[types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg'), prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        safety_settings=safety_settings,
                        image_config=types.ImageConfig(aspect_ratio="3:
