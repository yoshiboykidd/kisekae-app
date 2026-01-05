import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import base64

# --- API設定（Streamlit CloudのSecretsから読み込む設定） ---
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

st.set_page_config(layout="wide", page_title="AI KISEKAE Professional")

# 高級感のあるUIデザイン
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stButton>button { background: linear-gradient(to right, #1a2a6c, #b21f1f); color: white; border: none; height: 3.5em; font-weight: bold; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 AI KISEKAE Absolute Pro")

col_left, col_right = st.columns([1, 1.5])

with col_left:
    st.subheader("⚙️ 制約設定")
    source_img = st.file_uploader("1. 元写真をアップロード", type=['png', 'jpg', 'jpeg'])
    
    cloth = st.selectbox("2. 服装を選ぶ", 
        ["清楚な白ワンピース", "タイトな赤いドレス", "ナース服", "OL風オフィスカジュアル", 
         "紺色の学生服", "セクシーなビキニ", "黒のバニーガール", "和装（浴衣）", "メイド服"])
    
    bg = st.selectbox("3. 背景を選ぶ", 
        ["高級ホテルのスイートルーム", "夜の繁華街", "撮影スタジオ", "ビーチ", "落ち着いたカフェ"])

    st.divider()
    run_button = st.button("✨ 条件を厳守して生成を開始")

with col_right:
    st.subheader("🖼️ 生成結果 (600x800)")
    if run_button and source_img:
        with st.spinner("骨格・スタイル・表情を固定して生成中..."):
            try:
# 【最終手段：笑顔という単語を排除したプロンプト】
                prompt = (
                    f"STRICT CONSTRAINTS: "
                    f"1. FACE & IDENTITY: Use the EXACT SAME Japanese woman from the reference image. "
                    f"2. PHYSIQUE: Strictly maintain her original bone structure and body proportions. "
                    f"3. MOUTH (ABSOLUTE): MOUTH MUST BE COMPLETELY SEALED. LIPS ARE TOUCHING. NO GAP BETWEEN LIPS. " # 「完全に封印」「唇が触れている」「隙間なし」を徹底
                    f"4. EXPRESSION: A calm, serene, and pleasant facial expression with eyes slightly relaxed. " # 「笑顔」という言葉を使わず、「穏やかで心地よい表情、目元はリラックス」に変更
                    f"5. NO TEETH MANDATE: Absolutely ZERO visibility of teeth or inside of mouth under any circumstances. " # 「いかなる状況でも歯の露出はゼロ」と強調
                    f"SCENE: Wearing {cloth}. Background is {bg}. "
                    f"QUALITY: Photorealistic, 8k, professional studio lighting. "
                )

                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=[types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg'), prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        image_config=types.ImageConfig(aspect_ratio="3:4")
                    )
                )

                img_data = None
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        img_data = part.inline_data.data
                        break
                
                if img_data:
                    generated_img = Image.open(io.BytesIO(img_data))
                    final_img = generated_img.resize((600, 800)) # 指定サイズ固定 [User Rule]
                    
                    buffered = io.BytesIO()
                    final_img.save(buffered, format="JPEG", quality=95)
                    img_base64 = base64.b64encode(buffered.getvalue()).decode()
                    
                    # クラウド環境で安定して表示するためのHTML表示
                    st.markdown(f'<img src="data:image/jpeg;base64,{img_base64}" width="100%">', unsafe_allow_html=True)
                    
                    st.download_button("💾 画像を保存する", data=buffered.getvalue(), file_name="kisekae_hq.jpg", mime="image/jpeg")
                    st.success("生成完了！")
                else:
                    st.error("画像データが取得できませんでした。")
            except Exception as e:
                st.error(f"エラー: {e}")
