import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 認証機能 (karin10) ---
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

    st.title("📸 AI KISEKAE [High-Consistency Mode]")

    # 構図の「スロット」を定義し、被りを物理的に排除
    POSE_SLOTS = {
        "A: 全身立ち姿": "A full-length standing shot from the front, showing the entire outfit.",
        "B: 斜め・動き": "A 45-degree angle dynamic shot, walking or posing with one hand on hip.",
        "C: 座り・床ポーズ": "A shot of the person sitting elegantly on a chair or floor, showcasing the dress flow.",
        "D: クローズアップ": "A waist-up close-up shot, focusing on the face and upper body details."
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. キャスト写真 (必須)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. スタイル参照画像 (任意)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル設定", ["リゾートビキニ", "タイトミニドレス", "清楚ワンピース", "ナース服", "バニーガール", "メイド服", "浴衣"])
        cloth_detail = st.text_input("衣装の追加指示", placeholder="例：黒のレース素材、赤いリボン")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "ビーチ"])
        st.divider()
        run_button = st.button("✨ 4ポーズを完全分離生成")

    if run_button and source_img:
        st.subheader("🖼️ 生成結果 (ポーズ分離・衣装固定)")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        base_parts = [types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # 各スロット（A, B, C, D）ごとに生成
        for i, (slot_name, pose_instruction) in enumerate(POSE_SLOTS.items()):
            with placeholders[i]:
                with st.spinner(f"生成中: {slot_name}"):
                    try:
                        # 衣装の「完全固定」をAIに命じる
                        if ref_img:
                            cloth_task = (
                                f"FIXED OUTFIT: You must replicate the IDENTICAL outfit from IMAGE 2. "
                                f"Do not change colors, patterns, or materials. It is a {cloth_main}. "
                                f"Apply every detail of the '{cloth_detail}' consistently across this image."
                            )
                        else:
                            cloth_task = f"A consistent {cloth_main}. {cloth_detail}."

                        prompt = (
                            f"TASK: Generate a photo of the woman from IMAGE 1. "
                            f"COMPOSITION: {pose_instruction} " # スロット別の構図
                            f"OUTFIT: {cloth_task} "
                            f"BACKGROUND: {bg} with intense professional bokeh. "
                            f"FACE RULES: LIPS SEALED, NO TEETH. Strictly identical to IMAGE 1. "
                            f"QUALITY: 8k, photorealistic masterpiece, sharp focus on subject."
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
                            st.image(img, caption=slot_name, use_container_width=True)
                            
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p_{i+1}.jpg", mime="image/jpeg", key=f"btn_{i}")
                    except Exception as e:
                        st.error(f"エラー: {e}")
                    time.sleep(1.5) # AIの思考をリセットするために少し待ち時間を延長

st.markdown("---")
st.caption("© 2026 Karinto Group - High-Consistency Pose Engine")
