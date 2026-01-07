import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 認証機能 (合言葉: karin10) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 Karinto Group Image Tool")
        pwd = st.text_input("合言葉を入力してください", type="password")
        if st.button("ログイン"):
            if pwd == "karin10": 
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("合言葉が正しくありません")
        return False
    return True

# --- 2. メインアプリ ---
if check_password():
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)

    st.title("📸 AI KISEKAE Manager [Reference Mode]")

    # 大胆なポーズ集
    POSE_LIBRARY = {
        "Standard (王道)": [
            "Full body shot, walking toward camera, dress fluttering.",
            "High angle full body shot, looking up at camera.",
            "Full body shot, sitting on high stool, one leg stretched.",
            "Full body shot, leaning against marble pillar.",
            "Full body shot, side view, looking back with a smile.",
            "Full body shot, standing with a slight twist in waist.",
            "Full body shot, sitting on stairs, legs at different levels."
        ],
        "Cool & Sexy (大胆)": [
            "Low angle full body shot, sharp gaze downward.",
            "Full body shot, sitting on floor, leaning back on hands.",
            "Full body shot, back view, bold look over shoulder.",
            "Full body shot, lying on luxury sofa, long body line.",
            "Full body shot, leaning against wall, one knee bent.",
            "Full body shot, powerful model walk stride.",
            "Full body shot, squatting in high-fashion pose."
        ],
        "Cute & Active (動き)": [
            "Full body shot, jumping slightly, joyful expression.",
            "Full body shot, twirling around, skirt expanding.",
            "Full body shot, kneeling on carpet, holding pillow.",
            "Full body shot, crouching and peeking into camera.",
            "Full body shot, running on beach, wind-blown hair.",
            "Full body shot, sitting on swing, legs swinging."
        ]
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. キャスト写真 (必須)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 服装写真 (任意)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. 服装系統", ["清楚ワンピース", "タイトミニドレス", "ナース服", "バニーガール", "メイド服", "リゾートビキニ", "浴衣"])
        cloth_detail = st.text_input("詳細指定", placeholder="例：黒サテン、赤リボン")
        vibe_choice = st.selectbox("4. Vibe", list(POSE_LIBRARY.keys()))
        bg = st.selectbox("5. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "ビーチ"])
        st.divider()
        run_button = st.button("✨ 4枚一括生成")

    if run_button and source_img:
        selected_poses = random.sample(POSE_LIBRARY[vibe_choice], 4)
        st.subheader(f"🖼️ 生成結果 [{vibe_choice}]")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        base_parts = [types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        for i, pose_text in enumerate(selected_poses):
            with placeholders[i]:
                with st.spinner(f"生成中... {i+1}/4"):
                    try:
                        cloth_task = f"High-quality {cloth_main}. {cloth_detail}."
                        if ref_img:
                            cloth_task = f"REPLICATE the EXACT outfit from IMAGE 2. {cloth_main}, {cloth_detail}."

                        prompt = (
                            f"TASK: Keeping face of IMAGE 1, change outfit and background. "
                            f"COMPOSITION: {pose_text} OUTFIT: {cloth_task} "
                            f"BACKGROUND: {bg} with bokeh. "
                            f"RULES: LIPS SEALED, NO TEETH. Sharp focus on person. "
                            f"IDENTITY: Exact facial features of woman in IMAGE 1. "
                            f"QUALITY: 8k, photorealistic masterpiece."
                        )

                        response = client.models.generate_content(
                            model='gemini-3-pro-image-preview',
                            contents=base_parts + [prompt],
                            config=types.GenerateContentConfig(
                                response_modalities=['IMAGE'],
                                safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')],
                                image_config=types.ImageConfig(aspect_ratio="2:3")
                            )
                        )

                        if response.candidates and response.candidates[0].content.parts:
                            img_data = response.candidates[0].content.parts[0].inline_data.data
                            img = Image.open(io.BytesIO(img_data)).resize((600, 900))
                            st.image(img, use_container_width=True)
                            
                            # ダウンロードボタンの構文を安全に記述
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG")
                            btn_name = f"pose_{i+1}.jpg"
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=btn_name, mime="image/jpeg")
                        else:
                            st.error("生成失敗")
                    except Exception as e:
                        st.error(f"エラー: {e}")
                    time.sleep(1)

st.markdown("---")
st.caption("© 2026 Karinto Group - Reference Image Engine")
