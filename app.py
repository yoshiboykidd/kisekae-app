import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import base64

# --- API設定 ---
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

st.set_page_config(layout="wide", page_title="AI KISEKAE Perfect Pro")

# UIデザイン
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stButton>button { background: linear-gradient(to right, #1a2a6c, #b21f1f); color: white; border: none; height: 3.5em; font-weight: bold; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 AI KISEKAE Manager [エラー対策済]")

col_left, col_right = st.columns([1, 1.5])

with col_left:
    st.subheader("⚙️ 生成設定")
    source_img = st.file_uploader("1. 元写真をアップロード", type=['png', 'jpg', 'jpeg'])
    
    cloth = st.selectbox("2. 服装を選ぶ", 
        ["清楚な白ワンピース", "タイトな赤いドレス", "ナース服", "OL風オフィスカジュアル", 
         "紺色の学生服", "セクシーなビキニ", "黒のバニーガール", "和装（浴衣）", "メイド服"])
    
    bg = st.selectbox("3. 背景を選ぶ", 
        ["高級ホテルのスイートルーム", "夜の繁華街", "撮影スタジオ", "ビーチ", "落ち着いたカフェ"])

    st.divider()
    run_button = st.button("✨ 生成を開始（歯出し厳禁）")

with col_right:
    st.subheader("🖼️ 生成結果")
    if run_button and source_img:
        with st.spinner("生成中..."):
            try:
                # 【最終仕上げ：物理的口閉じ＋背景ボケ追加プロンプト】
                prompt = (
                    f"STRICT CONSTRAINTS (PRIORITY: MOUTH & FOCUS): "
                    # --- 1. 歯を物理的に封じる ---
                    f"1. MOUTH SEALED: Lips are firmly pressed flesh-to-flesh touching together completely. No parting line, no gap. "
                    f"2. NO TEETH VISIBLE: Absolutely zero white enamel or teeth structures visible anywhere. "
                    # --- 2. 背景をプロっぽくぼかす ---
                    f"3. FOCUS & BOKEH: Professional portrait photography with shallow depth of field. Sharp focus is ONLY on the woman's eyes and face. The background ({bg}) is smoothly blurred with beautiful soft bokeh. Aperture f/1.8 style. "
                    # --- 3. 基本設定 ---
                    f"4. EXPRESSION: Calm, serene, neutral facial expression with sealed lips. "
                    f"5. IDENTITY: Use the EXACT SAME Japanese woman from the reference image. Keep her bone structure. "
                    f"SCENE: Wearing {cloth}. "
                    f"QUALITY: Photorealistic, 8k, professional lighting. "
                )

                # 安全フィルターの緩和設定
                safety_settings = [
                    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
                ]

                # 生成実行
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=[types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg'), prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        safety_settings=safety_settings, # フィルター設定を適用
                        image_config=types.ImageConfig(aspect_ratio="3:4")
                    )
                )

                # エラー回避：結果が存在するか確認
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
                        img_base64 = base64.b64encode(buffered.getvalue()).decode()
                        
                        st.markdown(f'<img src="data:image/jpeg;base64,{img_base64}" width="100%">', unsafe_allow_html=True)
                        st.download_button("💾 画像を保存する", data=buffered.getvalue(), file_name="kisekae.jpg", mime="image/jpeg")
                    else:
                        st.warning("AIが画像を生成しませんでした。プロンプトや衣装を変更してみてください。")
                else:
                    # フィルターでブロックされた場合の表示
                    st.error("⚠️ 安全フィルターにより生成がブロックされました。より露出の少ない衣装や、別の写真で試してください。")

            except Exception as e:
                st.error(f"システムエラー: {e}")
