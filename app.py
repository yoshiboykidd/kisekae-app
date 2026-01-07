import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 認証機能 ---
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

    st.title("📸 AI KISEKAE Manager [Dynamic 4-Pose]")

    # --- 大胆に進化したポーズ・ライブラリ ---
    POSE_LIBRARY = {
        "Standard (王道)": [
            "Full body shot, walking confidently toward the camera, dress fluttering.", # 動き
            "High angle full body shot, looking up at the camera with a bright expression.", # アングル
            "Full body shot, sitting on a high stool, one leg stretched forward elegantly.", # 重心
            "Full body shot, leaning against a luxury car or marble pillar.", # 奥行き
            "Full body shot, captured from the side, looking back with a soft smile.",
            "Full body shot, standing with a slight twist in the waist to emphasize curves.",
            "Full body shot, sitting on stairs, legs positioned at different levels.",
            "Full body shot, reaching out a hand toward the camera naturally."
        ],
        "Cool & Sexy (大胆・綺麗め)": [
            "Dramatic low angle full body shot, looking down at the camera with a sharp gaze.", # 強気アングル
            "Full body shot, sitting on the floor with legs crossed, leaning back on hands.", # フロアポーズ
            "Full body shot, back view, looking over the shoulder with a bold expression.", # 背中
            "Full body shot, lying on a luxury sofa, showcasing a long body line.", # 寝そべり
            "Full body shot, leaning against a wall with one knee bent and foot up.", # 立体感
            "Full body shot, powerful model walk, captured in mid-stride.",
            "Full body shot, squatting elegantly in a high-fashion pose.",
            "Full body shot, arched back, arms raised slightly to highlight the silhouette."
        ],
        "Cute & Active (動きのある可愛さ)": [
            "Full body shot, jumping slightly or skipping with a joyful expression.", # 躍動感
            "Full body shot, twirling around, skirt expanding in a circle.", # 動き
            "Full body shot, kneeling on a soft carpet, holding a plush pillow.", # 幼さ
            "Full body shot, crouching down and peeking into the camera lens.", # 寄り
            "Full body shot, running gently on a beach, hair wind-blown and messy-cute.",
            "Full body shot, sitting on a swing or garden bench, legs swinging.",
            "Full body shot, hugging herself gently, tilted head and winking.",
            "Full body shot, hands in hair, leaning back with a playful laugh."
        ]
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. 元写真をアップロード", type=['png', 'jpg', 'jpeg'])
        
        cloth_main = st.selectbox("2. 服装の系統", ["清楚ワンピース", "タイトミニドレス", "ナース服", "バニーガール", "メイド服", "リゾートビキニ", "浴衣"])
        cloth_detail = st.text_input("詳細指定（色、素材など）", placeholder="例：黒のサテン地、赤いリボン")
        
        vibe_choice = st.selectbox("3. ポーズの雰囲気 (Vibe)", list(POSE_LIBRARY.keys()))
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "ビーチ"])
        
        st.divider()
        run_button = st.button("✨ 大胆な4枚を生成")

    if run_button and source_img:
        selected_poses = random.sample(POSE_LIBRARY[vibe_choice], 4)
        
        st.subheader(f"🖼️ 生成結果 [{vibe_choice}]")
        cols_row1 = st.columns(2)
        cols_row2 = st.columns(2)
        placeholders = [cols_row1[0], cols_row1[1], cols_row2[0], cols_row2[1]]

        for i, pose_text in enumerate(selected_poses):
            with placeholders[i]:
                with st.spinner(f"デザイン {i+1}..."):
                    try:
                        prompt = (
                            f"IMAGE EDITING TASK: Change clothes and background while keeping the face. "
                            f"COMPOSITION: {pose_text} " 
                            f"OUTFIT: A high-quality {cloth_main}. {cloth_detail}. "
                            f"BACKGROUND: {bg} with professional bokeh blur. "
                            f"MOUTH (STRICT): LIPS MUST BE SEALED TOGETHER. NO TEETH VISIBLE. "
                            f"FOCUS: Razor-sharp focus on the entire person. No blur on the subject. "
                            f"IDENTITY: Keep the exact facial features of the Japanese woman in the reference."
                            f"QUALITY: Photorealistic photography, 8k, masterpiece."
                        )

                        response = client.models.generate_content(
                            model='gemini-3-pro-image-preview',
                            contents=[types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg'), prompt],
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
                            
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"pose_{i+1}.jpg", mime="image/jpeg")
                        else:
                            st.error(f"生成失敗")
                    except Exception as e:
                        st.error(f"エラー: {e}")
                    time.sleep(1)

st.markdown("---")
st.caption("© 2026 Karinto Group - Dynamic Pose Engine")
