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

    st.title("📸 AI KISEKAE Manager [Pose Master Edition]")

    # --- 拡張されたポーズ・ライブラリ ---
    POSE_LIBRARY = {
        "Standard (王道全身)": [
            "Full body shot, standing straight, facing forward.",
            "Full body shot, walking confidently toward the camera.",
            "Full body shot, posing from a 45-degree angle, hand on hip.",
            "Full body shot, standing with legs crossed elegantly.",
            "Full body shot, leaning against a luxury pillar.",
            "Full body shot, captured from the side, looking back with a smile."
        ],
        "Cool & Sexy (大胆・綺麗め)": [
            "Dramatic low angle full body shot, looking down at the camera.",
            "Full body shot, back view, bold look over the shoulder.",
            "Full body shot, powerful model walk stride.",
            "Full body shot, leaning against a wall with one knee bent.",
            "Full body shot, arched back slightly to highlight the silhouette.",
            "Full body shot, squatting elegantly in a high-fashion pose."
        ],
        "Cute & Sweet (可愛い・動き)": [
            "Full body shot, jumping slightly with a joyful expression.",
            "Full body shot, twirling around, skirt expanding.",
            "Full body shot, hands on cheeks, tilted head.",
            "Full body shot, playing with hair, looking charming.",
            "Full body shot, hugging herself gently, winking.",
            "Full body shot, running gently, hair wind-blown."
        ],
        "Lying & Floor (寝そべり・床座り)": [
            "Full body shot, lying on a luxury sofa, showcasing a long body line.",
            "Full body shot, sitting on the floor with legs crossed, leaning back.",
            "Full body shot, kneeling on a soft carpet, looking into the camera.",
            "Full body shot, lying on a bed with a relaxed and inviting pose.",
            "Full body shot, sitting on the edge of a pool, legs in water.",
            "Full body shot, crouching low on the ground, high-fashion style."
        ],
        "Close-up & Face (顔寄り・表情重視)": [
            "Extreme close-up, focusing on the face and shoulders, intense gaze.",
            "Waist-up shot, hand near the face, highlighting the jewelry and expression.",
            "Close-up, looking through the fingers, mysterious mood.",
            "Upper body shot, leaning forward toward the camera lens.",
            "Profile shot, focusing on the facial line and neck.",
            "Close-up, chin resting on hands, soft and dreamy look."
        ],
        "Artistic & Dynamic (芸術的・大胆)": [
            "Full body shot, captured from a very high bird's-eye view.",
            "Full body shot, silhouette pose against a bright window.",
            "Full body shot, motion blur effect to show rapid movement.",
            "Full body shot, dramatic lighting with heavy shadows, mysterious pose.",
            "Full body shot, interacting with a luxury prop like a velvet curtain.",
            "Full body shot, posing like a statue, avant-garde style."
        ]
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. キャスト写真 (必須)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. スタイル参照画像 (任意)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. 強制するスタイル（形）", ["リゾートビキニ", "タイトミニドレス", "清楚ワンピース", "ナース服", "バニーガール", "メイド服", "浴衣"])
        cloth_detail = st.text_input("追加の指示", placeholder="例：フリル多め、地雷系デザインを移植")
        vibe_choice = st.selectbox("4. Vibe (ポーズ集)", list(POSE_LIBRARY.keys()))
        bg = st.selectbox("5. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "ビーチ"])
        st.divider()
        run_button = st.button("✨ 4枚一括生成開始")

    if run_button and source_img:
        # 選択されたVibeからランダムに4つ抽出
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
                        # スタイル融合ロジック
                        if ref_img:
                            cloth_task = (
                                f"Create a HYBRID OUTFIT. The SHAPE must be a {cloth_main}. "
                                f"STRICTLY APPLY the visual elements (color palette, patterns, ribbons, lace) from IMAGE 2 onto this {cloth_main}. "
                                f"Do NOT copy the clothing shape from IMAGE 2; only use its style DNA. {cloth_detail}."
                            )
                        else:
                            cloth_task = f"A high-quality {cloth_main}. {cloth_detail}."

                        prompt = (
                            f"TASK: Keeping the exact face of IMAGE 1, generate a professional photo. "
                            f"COMPOSITION: {pose_text} "
                            f"OUTFIT: {cloth_task} "
                            f"BACKGROUND: {bg} with professional bokeh. "
                            f"RULES: LIPS SEALED, NO TEETH VISIBLE. Razor-sharp focus on the subject. " # 黄金ルール
                            f"IDENTITY: Strictly preserve the facial features of the woman in IMAGE 1."
                            f"QUALITY: 8k, photorealistic studio photography, masterpiece."
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
                            
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p_{i+1}.jpg", mime="image/jpeg")
                        else:
                            st.error("生成失敗")
                    except Exception as e:
                        st.error(f"エラー: {e}")
                    time.sleep(1)

st.markdown("---")
st.caption("© 2026 Karinto Group - Ultimate Pose Library")
