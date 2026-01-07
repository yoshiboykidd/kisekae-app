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

    # --- 大胆なポーズ・ライブラリ ---
    POSE_LIBRARY = {
        "Standard (王道)": [
            "Full body shot, walking confidently toward the camera, dress fluttering.",
            "High angle full body shot, looking up at the camera with a bright expression.",
            "Full body shot, sitting on a high stool, one leg stretched forward elegantly.",
            "Full body shot, leaning against a luxury car or marble pillar.",
            "Full body shot, captured from the side, looking back with a soft smile.",
            "Full body shot, standing with a slight twist in the waist to emphasize curves.",
            "Full body shot, sitting on stairs, legs positioned at different levels."
        ],
        "Cool & Sexy (大胆・綺麗め)": [
            "Dramatic low angle full body shot, looking down at the camera with a sharp gaze.",
            "Full body shot, sitting on the floor with legs crossed, leaning back on hands.",
            "Full body shot, back view, looking over the shoulder with a bold expression.",
            "Full body shot, lying on a luxury sofa, showcasing a long body line.",
            "Full body shot, leaning against a wall with one knee bent and foot up.",
            "Full body shot, powerful model walk, captured in mid-stride.",
            "Full body shot, squatting elegantly in a high-fashion pose."
        ],
        "Cute & Active (動きのある可愛さ)": [
            "Full body shot, jumping slightly or skipping with a joyful expression.",
            "Full body shot, twirling around, skirt expanding in a circle.",
            "Full body shot, kneeling on a soft carpet, holding a plush pillow.",
            "Full body shot, crouching down and peeking into the camera lens.",
            "Full body shot, running gently on a beach, hair wind-blown and messy-cute.",
            "Full body shot, sitting on a swing or garden bench, legs swinging."
        ]
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. キャストの顔写真 (必須)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 参考にしたい服装の写真 (任意)", type=['png', 'jpg', 'jpeg'])
        
        st.divider()
        cloth_main = st.selectbox("3. 服装の系統", ["清楚ワンピース", "タイトミニドレス", "ナース服", "バニーガール", "メイド服", "リゾートビキニ", "浴衣"])
        cloth_detail = st.text_input("詳細指定（色、素材など）", placeholder="例：黒のサテン地、赤いリボン")
        vibe_choice = st.selectbox("4. ポーズの雰囲気 (Vibe)", list(POSE_LIBRARY.keys()))
        bg = st.selectbox("5. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "ビーチ"])
        
        st.divider()
        run_button = st.button("✨ 4枚一括生成開始")

    if run_button and source_img:
        selected_poses = random.sample(POSE_LIBRARY[vibe_choice], 4)
        
        # --- ここがエラー箇所でした。正しく修正済みです ---
        st.subheader(f"🖼️ 生成結果 [{vibe_choice}]")
        
        cols_row1 = st.columns(2)
        cols_row2 = st.columns(2)
        placeholders = [cols_row1[0], cols_row1[1], cols_row2[0], cols_row2[1]]

        # AIに渡す画像リストを作成
        base_parts = [types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        for i, pose_text in enumerate(selected_poses):
            with placeholders[i]:
                with st.spinner(f"デザイン {i+1}..."):
                    try:
                        # 参照画像がある場合、その服をコピーするようにAIへ強く指示
                        cloth_task = f"A high-quality {cloth_main}. {cloth_detail}."
                        if ref_img:
                            cloth_task = (
                                f"REPLICATE the EXACT outfit (color, pattern, material, design) from the SECOND reference image. "
                                f"The person should wear this {cloth_main}. {cloth_detail}."
                            )

                        prompt = (
                            f"TASK: Change clothes and background while keeping the face from IMAGE 1. "
                            f"COMPOSITION: {pose_text} " 
                            f"OUTFIT: {cloth_task} "
                            f"BACKGROUND: {bg} with intense bokeh blur. "
                            f"MOUTH: LIPS SEALED TOGETHER. NO TEETH VISIBLE. " # 不変のルール
                            f"FOCUS: Razor-sharp focus on the person. " 
                            f"IDENTITY: Keep the facial features of the Japanese woman in IMAGE 1."
                            f"QUALITY: Photorealistic, 8k, professional lighting."
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

                        if response.candidates and response.candidates[0].
