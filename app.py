import streamlit as st
from google import genai
from google.genai import types
from PIL import Image, ImageFilter, ImageDraw
import io
import os
import time
import random
import cv2
import numpy as np

# --- 1. ポーズ選出ロジック ---
def get_4_preset_poses(pattern="立ち3:座り1"):
    base_path = "presets/poses"
    stand_dir = os.path.join(base_path, "standing")
    sit_dir = os.path.join(base_path, "sitting")

    def get_set_ids(directory):
        if not os.path.exists(directory): return []
        files = os.listdir(directory)
        ids = []
        for f in files:
            parts = f.split('_')
            if len(parts) >= 2:
                # pose_001_Front.jpg -> pose_001 をIDとする
                ids.append(f"{parts[0]}_{parts[1]}")
        return sorted(list(set(ids)))

    def find_file(directory, set_id, angle_keywords):
        if not os.path.exists(directory): return None
        files = os.listdir(directory)
        for f in files:
            if f.startswith(set_id):
                for kw in angle_keywords:
                    if kw.lower() in f.lower():
                        return os.path.join(directory, f)
        return None

    stand_sets = get_set_ids(stand_dir)
    sit_sets = get_set_ids(sit_dir)

    if pattern == "立ち3:座り1" and (len(stand_sets) < 3 or len(sit_sets) < 1):
        st.error(f"セット不足: 立ち{len(stand_sets)}, 座り{len(sit_sets)}")
        return []
    
    selected_paths = []
    try:
        if pattern == "立ち3:座り1":
            chosen_s = random.sample(stand_sets, 3)
            chosen_t = random.sample(sit_sets, 1)
            selected_paths.append(find_file(stand_dir, chosen_s[0], ["Front", "Frot"]))
            selected_paths.append(find_file(stand_dir, chosen_s[1], ["Quarter"]))
            selected_paths.append(find_file(stand_dir, chosen_s[2], ["Low"]))
            selected_paths.append(find_file(sit_dir, chosen_t[0], ["High"]))
        else:
            chosen_s = random.sample(stand_sets, 2)
            chosen_t = random.sample(sit_sets, 2)
            selected_paths.append(find_file(stand_dir, chosen_s[0], ["Front", "Frot"]))
            selected_paths.append(find_file(stand_dir, chosen_s[1], ["Low"]))
            selected_paths.append(find_file(sit_dir, chosen_t[0], ["Quarter"]))
            selected_paths.append(find_file(sit_dir, chosen_t[1], ["High"]))
    except Exception as e:
        st.error(f"ポーズ選出エラー: {e}")
        return []

    return [p for p in selected_paths if p is not None]

# --- 2. 顔ブラー処理 (楕円形＆強度選択対応) ---
def apply_face_blur(pil_image, blur_radius):
    # OpenCVで顔検出
    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5)
    
    if len(faces) == 0:
        return pil_image

    # 1. 画像全体に指定強度のブラーをかけた画像を作成
    blurred_image = pil_image.filter(ImageFilter.GaussianBlur(blur_radius))

    # 2. 楕円形のマスク画像を作成（黒背景に白い楕円）
    mask = Image.new('L', pil_image.size, 0) # 'L'はグレイスケールモード
    draw = ImageDraw.Draw(mask)
    
    for (x, y, w, h) in faces:
        # 楕円の範囲を少し広げる（上下左右に15%ずつ）
        margin_w = int(w * 0.15)
        margin_h = int(h * 0.15)
        ellipse_box = [
            x - margin_w,         # 左
            y - margin_h * 1.2,   # 上（少し多めに）
            x + w + margin_w,     # 右
            y + h + margin_h      # 下
        ]
        # 白い楕円を描画
        draw.ellipse(ellipse_box, fill=255, outline=255)

    # マスクの境界を少しぼかして自然にする
    mask_blurred = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius/2))

    # 3. 元画像とブラー画像をマスクを使って合成
    # マスクが白い部分（楕円）はブラー画像、黒い部分は元画像が使われる
    final_image = Image.composite(blurred_image, pil_image, mask_blurred)
    
    return final_image

# --- 3. 認証機能 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 Karinto Group Image Tool")
        pwd = st.text_input("合言葉", type="password")
        if st.button("ログイン"):
            if pwd == "karin10": 
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("不一致")
        return False
    return True

# --- 4. メインアプリ ---
if check_password():
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
    st.title("📸 AI KISEKAE Manager")

    with st.sidebar:
        st.subheader("👤 写真アップロード")
        source_img = st.file_uploader("キャスト写真", type=['png', 'jpg', 'jpeg'])
        if source_img: st.image(source_img, use_container_width=True)
        
        ref_img = st.file_uploader("衣装参考 (任意)", type=['png', 'jpg', 'jpeg'])
        if ref_img: st.image(ref_img, use_container_width=True)
            
        st.divider()
        cloth_main = st.selectbox("ベース衣装", ["タイトミニドレス", "清楚ワンピース", "水着", "浴衣", "ナース服"])
        cloth_detail = st.text_input("追加指示", placeholder="例：黒サテン")
        bg = st.selectbox("背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "ビーチ"])
        pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
        
        st.divider()
        st.subheader("🛡️ プライバシー保護")
        enable_blur = st.checkbox("自動顔ブラーを適用", value=True)
        
        # --- 追加：ブラー強度選択スライダー ---
        blur_strength = "中" # デフォルト
        if enable_blur:
            blur_strength = st.select_slider(
                "ブラー強度を選択",
                options=["弱", "中", "強"],
                value="中"
            )
        
        st.divider()
        run_button = st.button("✨ 4枚一括生成")

    if run_button and source_img:
        pose_paths = get_4_preset_poses(pose_pattern)
        
        if pose_paths:
            st.subheader("🖼️ 生成結果")
            row1 = st.columns(2)
            row2 = st.columns(2)
            placeholders = [row1[0], row1[1], row2[0], row2[1]]

            identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')
            style_part = None
            if ref_img:
                style_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')

            # ブラー強度の数値変換マップ
            blur_radius_map = {"弱": 15, "中": 30, "強": 60}
            current_blur_radius = blur_radius_map[blur_strength]

            for i, path in enumerate(pose_paths):
                angle_label = path.split('_')[-1].split('.')[0]
                with placeholders[i]:
                    with st.spinner(f"{angle_label}生成中..."):
                        try:
                            with open(path, "rb") as f:
                                pose_part = types.Part.from_bytes(data=f.read(), mime_type='image/jpeg')
                            
                            contents = [identity_part]
                            if style_part: contents.append(style_part)
                            contents.append(pose_part)

                            prompt = (
                                f"IDENTITY (IMAGE 1): Absolute match. Copy face and bone structure 100%.\n"
                                f"POSE (IMAGE 3): Follow this exact skeletal pose and camera angle.\n"
                                f"OUTFIT: A {cloth_main}. {cloth_detail}.\n"
                                f"RULES: Japanese woman. Lips sealed, no teeth. 8k photorealistic. Background: {bg}."
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
                                
                                # 楕円形＆指定強度のブラーを適用
                                if enable_blur:
                                    final_img = apply_face_blur(raw_img, current_blur_radius)
                                else:
                                    final_img = raw_img
                                    
                                st.image(final_img, caption=f"View: {angle_label}", use_container_width=True)
                                
                                buf = io.BytesIO()
                                final_img.save(buf, format="JPEG")
                                st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"k_{i+1}.jpg", key=f"dl_{i}")
                            else:
                                st.error("AI判定でスキップされました")
                        except Exception as e:
                            st.error(f"エラー: {e}")
                        time.sleep(1.2)
