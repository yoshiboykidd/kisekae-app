import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import base64

# --- API設定 ---
# Streamlit CloudのAdvanced settings > Secrets に保存したキーを使用
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

st.set_page_config(layout="wide", page_title="AI KISEKAE Manager Pro")

# --- UIデザイン (ダークでプロ仕様) ---
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #ffffff; }
    .stSelectbox label, .stFileUploader label { color: #ffffff !important; font-weight: bold; }
    .stButton>button { 
        background: linear-gradient(45deg, #FF0000, #8B0000); 
        color: white; border: none; height: 3.5em; font-weight: bold; width: 100%; border-radius: 10px;
    }
    .stButton>button:hover { background: linear-gradient(45deg, #8B0000, #FF0000); }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 AI KISEKAE Manager [Ultimate Edition]")

col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("⚙️ 生成設定")
    source_img = st.file_uploader("1. 元写真をアップロード (キャストの顔)", type=['png', 'jpg', 'jpeg'])
    
    # バニーガールの名前を回避名に変更
    cloth = st.selectbox("2. 服装を選ぶ", 
        ["清楚な白ワンピース", "タイトな赤いドレス", "ナース服", "OL風オフィスカジュアル", 
         "紺色の学生服", "セクシーなビキニ", 
         "黒いレオタードとうさ耳カチューシャのコスチューム", 
         "和装（浴衣）", "メイド服"])
    
    bg = st.selectbox("3. 背景を選ぶ", 
        ["高級ホテルのスイートルーム", "夜の繁華街", "撮影スタジオ", "リゾートビーチ", "落ち着いたカフェ"])

    st.divider()
    run_button = st.button("✨ 高画質生成を開始")

with col_right:
    st.subheader("🖼️ 生成結果")
    if run_button and source_img:
        with st.spinner("AIが緻密に描画中..."):
            try:
                # 【鉄壁のプロンプト構成：物理的封印 ＋ 背景ボケ ＋ フィルター回避】
                prompt = (
                    f"STRICT CONSTRAINTS
