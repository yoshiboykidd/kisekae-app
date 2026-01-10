import streamlit as st
from google import genai
from google.genai import types
from PIL import Image, ImageFilter
import io
import os
import time
import random
import cv2
import numpy as np

# --- 1. ポーズ選出ロジック (アングル・セット重複回避) ---
def get_4_preset_poses(pattern="立ち3:座り1"):
    base_path = "presets/poses"
    stand_dir = os.path.join(base_path, "standing")
    sit_dir = os.path.join(base_path, "sitting")

    def get_set_ids(directory):
        if not os.path.exists(directory): return []
        # ファイル名から "pose001" 等のID部分を抽出して重複を除く
        files = os.listdir(directory)
        return sorted(list(set([f.split('_')[0] for f in files if "_" in f])))

    stand_sets = get_set_ids(stand_dir)
    sit_sets = get_set_ids(sit_dir)

    if not stand_sets or not sit_sets:
        return []

    selected_paths = []
    
    if pattern == "立ち3:座り1":
        # 立ちから3セット、座りから1セットを重複なしで選出
        chosen_s = random.sample(stand_sets, 3)
        chosen_t = random.sample(sit_sets, 1)
        
        # アングルを割り振り (Front, Quarter, Low / High)
        selected_paths.append(os.path.join(stand_dir, f"{chosen_s[0]}_Front.jpg"))
        selected_paths.append(os.path.join(stand_dir, f"{chosen_s[1]}_Quarter.jpg"))
        selected_paths.append(os.path.join(stand_dir, f"{chosen_s[2]}_Low.jpg"))
        selected_paths.append(os.path.join(sit_dir, f"{chosen_t[0]}_High.jpg"))
        
    else: # 立ち2:座り2
        chosen_s = random.sample(stand_sets, 2)
        chosen_t = random.sample(sit_sets, 2)
        
        selected_paths.append(os.path.join(stand_dir, f"{chosen_s[0]}_Front.jpg"))
        selected_paths.append(os.path.join(stand_dir, f"{chosen_s[1]}_Low.jpg"))
        selected_paths.append(os.path.join(sit_dir, f"{chosen_t[0]}_Quarter.jpg"))
        selected_paths.append(os.path.join(sit_dir, f"{chosen_t[1]}_High.jpg"))

    return selected_paths

# --- 2. 顔ブラー処理 (確実な加工) ---
def apply_face_blur(pil_image, blur_radius=25):
    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5)
    
    pil_draw_image = pil_image.copy()
    for (x, y, w, h) in faces:
        margin = int(w * 0.15)
        x1, y1 = max(0, x - margin), max(0, y - margin)
        x2, y2 = min(pil_image.width, x + w + margin), min(pil_image.height, y + h + margin)
        face_region = pil_draw_image.crop((x1, y1, x2, y2))
        blurred_region = face_region.filter(ImageFilter.GaussianBlur(blur_radius))
        pil_draw_image.paste(blurred_region, (x1, y1))
    return pil_draw_image

# --- 3. 認証機能 ---
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

# --- 4. メインアプリ ---
if check_password():
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)

    st.title("📸 AI KISEKAE [Identity Lock V5]")

    with st.sidebar:
        st.subheader("👤 1. キャスト（絶対遵守）")
        source_img = st.file_uploader("顔・体型ソース", type=['png', 'jpg', 'jpeg'])
        
        st.subheader("👗 2. 衣装・スタイル")
        ref_img = st.file_uploader("衣装参考画像 (任意)", type=['png', 'jpg', 'jpeg'])
        cloth_main = st.selectbox("ベース衣装", ["タイトミニドレス", "清楚ワンピース", "水着", "浴衣", "ナース服"])
        cloth_detail = st.text_input("追加指示", placeholder="例：黒サテン、赤リボン")
        
        st.subheader("🕺 3. ポーズ配分")
        pose_pattern = st.radio("比率選択", ["立ち3:座り1", "立ち2:座り2"])
        
        st.subheader("🏙️ 4. 背景・加工")
        bg = st.selectbox("背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "ビーチ"])
        enable_blur = st.checkbox("🛡️ 自動顔ブラーを有効化", value=True)
        
        st.divider()
        run_button = st.button("✨ 4枚一括生成開始")

    if run_button and source_img:
        pose_paths = get_4_preset_poses(pose_pattern)
        if not pose_paths:
            st.error("ポーズ画像が見つかりません。presets/poses/ の構成を確認してください。")
            st.stop()

        st.subheader(f"🖼️ 生成結果 ({pose_pattern})")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')
        style_part = None
        if ref_img:
            style_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')

        for i, path in enumerate(pose_paths):
            angle = path.split("_")[-1].replace(".jpg", "") # Front, Quarter, Low, High
            with placeholders[i // 2][i % 2]:
                with st.spinner(f"{angle}アングル生成中..."):
                    try:
                        with open(path, "rb") as f:
                            pose_part = types.Part.from_bytes(data=f.read(), mime_type='image/jpeg')
                        
                        contents = [identity_part]
                        if style_part: contents.append(style_part)
                        contents.append(pose_part)

                        prompt = (
                            f"MANDATORY: Maintain 100% facial and bone structure identity from IMAGE 1.\n"
                            f"POSE: Follow the exact 3D skeletal silhouette and '{angle}' camera angle from IMAGE 3.\n"
                            f"OUTFIT: A {cloth_main}. Extract texture DNA from IMAGE 2. {cloth_detail}.\n"
                            f"RULES: Japanese woman. Lips sealed, no teeth visible. 8k photorealistic. Background: {bg}."
                        )

                        response = client.models.generate_content(
                            model='gemini-3-pro-image-preview',
                            contents=contents + [prompt],
                            config=types.GenerateContentConfig(
                                response_modalities=['IMAGE'],
                                safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')],
                                image_config=types.ImageConfig(aspect_ratio="2:3")
                            )
                        )

                        if response.candidates and response.candidates[0].content.parts:
                            img_data = response.candidates[0].content.parts[0].inline_data.data
                            raw_img = Image.open(io.BytesIO(img_data)).resize((600, 900))
                            final_img = apply_face_blur(raw_img) if enable_blur else raw_img
                            st.image(final_img, caption=f"Pose Set {i+1} ({angle})", use_container_width=True)
                            
                            buf = io.BytesIO()
                            final_img.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p{i+1}.jpg", key=f"dl_{i}")
                    except Exception as e:
                        st.error(f"エラー: {e}")
                    time.sleep(1.0)
