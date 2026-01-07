import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

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

    st.title("📸 AI KISEKAE [Identity Lock Mode]")

    # 4つの構図を物理的に定義
    POSE_SLOTS = {
        "A: 正面（全身）": "A formal full-body fashion shot, standing straight, facing forward.",
        "B: 動き（全身）": "A dynamic full-body shot, walking or turning pose.",
        "C: 座り（全身）": "A full-body shot sitting elegantly on a chair or floor.",
        "D: 寄り（バストアップ）": "A beauty portrait shot from the chest up, focusing on the face."
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. キャスト写真 (顔：絶対遵守)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装参照画像 (柄：参考用)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル設定", ["ワンピースドレス", "タイトミニドレス", "オフィスカジュアル", "ナーススタイル", "メイドスタイル", "スイムウェア", "浴衣"])
        cloth_detail = st.text_input("衣装の追加指示", placeholder="例：黒のサテン地、フリル付き")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の街並み", "撮影スタジオ", "カフェテラス", "プライベートビーチ"])
        st.divider()
        run_button = st.button("✨ 4枚一括生成開始")

    if run_button and source_img:
        st.subheader("🖼️ 生成結果")
        cols_row1 = st.columns(2)
        cols_row2 = st.columns(2)
        placeholders = [cols_row1[0], cols_row1[1], cols_row2[0], cols_row2[1]]

        base_parts = [types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        for i, (slot_name, pose_instruction) in enumerate(POSE_SLOTS.items()):
            with placeholders[i]:
                with st.spinner(f"生成中... {i+1}/4"):
                    try:
                        # 指示の強度を最大化するためのプロンプト構成
                        if ref_img:
                            # 画像2の顔を「完全に無視しろ」と明文化
                            cloth_task = (
                                f"OUTFIT RULES: Strictly replicate the color, pattern, and texture from IMAGE 2. "
                                f"But DO NOT use the face or person from IMAGE 2. "
                                f"The final outfit must be a {cloth_main}. {cloth_detail}."
                            )
                        else:
                            cloth_task = f"OUTFIT: A high-quality {cloth_main}. {cloth_detail}."

                        prompt = (
                            f"STRICT INSTRUCTION 1 (FACE): You MUST generate the EXACT person from IMAGE 1. "
                            f"Keep her face, eyes, hair, and identity 100% identical to IMAGE 1. "
                            f"IGNORE any facial features from IMAGE 2. IMAGE 2 is only for cloth patterns. "
                            f"STRICT INSTRUCTION 2 (OUTFIT): {cloth_task} "
                            f"STRICT INSTRUCTION 3 (POSE): {pose_instruction} "
                            f"STRICT INSTRUCTION 4 (FACE EXPRESSION): Lips MUST be sealed together. Do NOT show teeth. "
                            f"ENVIRONMENT: {bg} with professional bokeh. "
                            f"STYLE: Photorealistic 8k studio photography, sharp focus on subject."
                        )

                        response = client.models.generate_content(
                            model='gemini-3-pro-image-preview',
                            contents=base_parts + [prompt],
                            config=types.GenerateContentConfig(
                                response_modalities=['IMAGE'],
                                safety_settings=[
                                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                                ],
                                image_config=types.ImageConfig(aspect_ratio="2:3")
                            )
                        )

                        if response.candidates and response.candidates[0].content.parts:
                            img_data = response.candidates[0].content.parts[0].inline_data.data
                            img = Image.open(io.BytesIO(img_data)).resize((600, 900))
                            st.image(img, caption=slot_name, use_container_width=True)
                            
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"pose_{i+1}.jpg", mime="image/jpeg", key=f"btn_{i}")
                        else:
                            st.error("AI規制によりブロックされました。服装や背景を変えてみてください。")
                    except Exception as e:
                        st.error(f"エラー発生: {e}")
                    
                    time.sleep(1.5)

st.markdown("---")
st.caption("© 2026 Karinto Group - Identity Lock Engine V4")
