import streamlit as st
from google import genai
from google.genai import types
from PIL import Image, ImageFilter
import io
import os
import time
import cv2
import numpy as np

# --- 1. 顔ブラー処理関数 (OpenCVで顔を検出し、Pillowでボカす) ---
def apply_face_blur(pil_image, blur_radius=25):
    # PIL画像をOpenCV形式(numpy配列)に変換
    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    # 顔検出用の学習済みモデル(Haar Cascade)を読み込み
    # Streamlit Cloud環境でも動作するよう標準パスを使用
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    
    # 顔を検出 (パラメータを調整して精度を確保)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    # 検出された顔領域にブラーをかける
    pil_draw_image = pil_image.copy()
    for (x, y, w, h) in faces:
        # 少し広めに範囲をとる (顔全体を隠すため)
        margin = int(w * 0.1)
        x1, y1 = max(0, x - margin), max(0, y - margin)
        x2, y2 = min(pil_image.width, x + w + margin), min(pil_image.height, y + h + margin)
        
        # 顔の領域を切り出してブラーを適用
        face_region = pil_draw_image.crop((x1, y1, x2, y2))
        blurred_region = face_region.filter(ImageFilter.GaussianBlur(blur_radius))
        # 元の画像に貼り戻す
        pil_draw_image.paste(blurred_region, (x1, y1))
        
    return pil_draw_image

# --- 2. 認証機能 (karin10) ---
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

# --- 3. メインアプリ ---
if check_password():
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)

    st.title("📸 AI KISEKAE [Identity Lock & Auto Blur]")

    # 4つの構図スロット
    POSE_SLOTS = {
        "A: 正面（全身）": "A formal full-body fashion shot, standing straight, facing forward.",
        "B: 動き（全身）": "A dynamic full-body shot, walking or turning pose.",
        "C: 座り（全身）": "A full-body shot sitting elegantly on a chair or floor.",
        "D: 寄り（バストアップ）": "A beauty portrait shot from the chest up, focusing on the face."
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. キャスト写真 (顔・体型ソース)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装参考画像 (ニュアンス用)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル設定", ["ワンピースドレス", "タイトミニドレス", "清楚ワンピース", "スイムウェア", "浴衣"])
        cloth_detail = st.text_input("衣装の追加指示", placeholder="例：黒サテン地、ピンクのリボン")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の街並み", "撮影スタジオ", "プライベートビーチ"])
        st.divider()
        # ★ブラーのON/OFFと強さを選べるように設定
        enable_blur = st.checkbox("🛡️ 最終画像に顔ブラーをかける", value=True)
        blur_strength = st.slider("ブラーの強さ", 10, 50, 25)
        st.divider()
        run_button = st.button("✨ 掟を守って4枚生成開始")

    if run_button and source_img:
        st.subheader("🖼️ 生成結果")
        cols_row1 = st.columns(2)
        cols_row2 = st.columns(2)
        placeholders = [cols_row1[0], cols_row1[1], cols_row2[0], cols_row2[1]]

        base_parts = [types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        for i, (slot_name, pose_instruction) in enumerate(POSE_SLOTS.items()):
            with placeholders[i // 2][i % 2]:
                with st.spinner(f"生成と加工中... {i+1}/4"):
                    try:
                        # 衣装融合ロジック
                        if ref_img:
                            cloth_task = (
                                f"OUTFIT DNA: Replicate ONLY the color and textile pattern from IMAGE 2. "
                                f"Apply this DNA onto a {cloth_main}. {cloth_detail}. "
                                f"Do NOT copy the person's body or face from IMAGE 2."
                            )
                        else:
                            cloth_task = f"OUTFIT: A high-quality {cloth_main}. {cloth_detail}."

                        # プロンプト：顔と骨格の絶対守護
                        prompt = (
                            f"STRICT INSTRUCTION 1 (IDENTITY): Generate the EXACT person from IMAGE 1. "
                            f"Her facial features and biological bone structure MUST be 100% identical to IMAGE 1. "
                            f"STRICT INSTRUCTION 2 (OUTFIT): {cloth_task} "
                            f"STRICT INSTRUCTION 3 (POSE): {pose_instruction} "
                            f"STRICT INSTRUCTION 4 (MOUTH): Lips sealed, NO TEETH visible. "
                            f"ENVIRONMENT: {bg}. Professional 8k photography, sharp focus."
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
                            raw_img = Image.open(io.BytesIO(img_data)).resize((600, 900))
                            
                            # --- ブラー処理の適用 ---
                            if enable_blur:
                                final_img = apply_face_blur(raw_img, blur_radius=blur_strength)
                            else:
                                final_img = raw_img

                            st.image(final_img, caption=slot_name, use_container_width=True)
                            
                            buf = io.BytesIO()
                            final_img.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p{i+1}.jpg", mime="image/jpeg", key=f"dl_{i}")
                        else:
                            st.error("ブロックされました。")
                    except Exception as e:
                        st.error(f"エラー: {e}")
                    time.sleep(1.2)
