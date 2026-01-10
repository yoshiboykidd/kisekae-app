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

# --- 1. ポーズ選出ロジック (ファイル名からセットとアングルを特定) ---
def get_4_preset_poses(pattern="立ち3:座り1"):
    base_path = "presets/poses"
    stand_dir = os.path.join(base_path, "standing")
    sit_dir = os.path.join(base_path, "sitting")

    def get_set_ids(directory):
        if not os.path.exists(directory):
            return []
        files = os.listdir(directory)
        # ファイル名から "pose001" 等のID部分を抽出して重複を除く
        return sorted(list(set([f.split('_')[0] for f in files if "_" in f])))

    stand_sets = get_set_ids(stand_dir)
    sit_sets = get_set_ids(sit_dir)

    if not stand_sets or not sit_sets:
        return []

    selected_paths = []
    
    # アングルの優先スロット
    if pattern == "立ち3:座り1":
        chosen_s = random.sample(stand_sets, min(3, len(stand_sets)))
        chosen_t = random.sample(sit_sets, min(1, len(sit_sets)))
        
        # 立ち3枚: Front, Quarter, Low
        selected_paths.append(os.path.join(stand_dir, f"{chosen_s[0]}_Front.jpg"))
        selected_paths.append(os.path.join(stand_dir, f"{chosen_s[1]}_Quarter.jpg"))
        selected_paths.append(os.path.join(stand_dir, f"{chosen_s[2]}_Low.jpg"))
        # 座り1枚: High
        selected_paths.append(os.path.join(sit_dir, f"{chosen_t[0]}_High.jpg"))
        
    else: # 立ち2:座り2
        chosen_s = random.sample(stand_sets, min(2, len(stand_sets)))
        chosen_t = random.sample(sit_sets, min(2, len(sit_sets)))
        
        selected_paths.append(os.path.join(stand_dir, f"{chosen_s[0]}_Front.jpg"))
        selected_paths.append(os.path.join(stand_dir, f"{chosen_s[1]}_Low.jpg"))
        selected_paths.append(os.path.join(sit_dir, f"{chosen_t[0]}_Quarter.jpg"))
        selected_paths.append(os.path.join(sit_dir, f"{chosen_t[1]}_High.jpg"))

    return selected_paths

# --- 2. 顔ブラー処理関数 ---
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
    # Streamlit SecretsからAPIキーを取得
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("APIキーが設定されていません。")
        st.stop()
        
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)

    st.title("📸 AI KISEKAE Manager")
    st.info("キャストのアイデンティティを保護しながら宣材写真を生成します。")

    with st.sidebar:
        st.subheader("👤 1. 写真アップロード")
        # --- キャスト写真 ---
        source_img = st.file_uploader("キャスト（顔・体型ソース）", type=['png', 'jpg', 'jpeg'])
        if source_img:
            st.image(source_img, caption="【確認】キャスト写真", use_container_width=True)
        
        st.divider()
        
        # --- 衣装参考写真 ---
        ref_img = st.file_uploader("衣装・素材参考 (任意)", type=['png', 'jpg', 'jpeg'])
        if ref_img:
            st.image(ref_img, caption="【確認】衣装参考", use_container_width=True)
            
        st.divider()
        
        st.subheader("👗 2. スタイル設定")
        cloth_main = st.selectbox("ベース衣装", ["タイトミニドレス", "清楚ワンピース", "スイムウェア", "浴衣", "ナース服"])
        cloth_detail = st.text_input("追加指示", placeholder="例：黒サテン、赤リボン")
        bg = st.selectbox("背景環境", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "プライベートビーチ"])
        
        st.subheader("🕺 3. ポーズ・加工")
        pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
        enable_blur = st.checkbox("🛡️ 自動顔ブラー（モザイク）を適用", value=True)
        
        st.divider()
        run_button = st.button("✨ 掟を守って4枚生成")

    # --- 生成実行セクション ---
    if run_button:
        if not source_img:
            st.warning("キャスト写真をアップロードしてください。")
        else:
            pose_paths = get_4_preset_poses(pose_pattern)
            if not pose_paths:
                st.error("GitHubのpresetsフォルダに画像が見つかりません。")
            else:
                st.subheader(f"🖼️ 生成結果 ({pose_pattern})")
                cols = [st.columns(2), st.columns(2)]
                placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

                identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')
                style_part = None
                if ref_img:
                    style_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')

                for i, path in enumerate(pose_paths):
                    # ファイル名からアングル名を抽出
                    angle_name = path.split("_")[-1].replace(".jpg", "")
                    
                    with placeholders[i // 2][i % 2]:
                        with st.spinner(f"{angle_name}アングルを生成中..."):
                            try:
                                # ポーズ見本画像の読み込み
                                with open(path, "rb") as f:
                                    pose_part = types.Part.from_bytes(data=f.read(), mime_type='image/jpeg')
                                
                                contents = [identity_part]
                                if style_part: contents.append(style_part)
                                contents.append(pose_part)

                                # プロンプト：役割分担の徹底
                                prompt = (
                                    f"TASK: Generate a photorealistic image.\n"
                                    f"IDENTITY (IMAGE 1): Absolute match. Copy her facial features and biological bone structure 100%.\n"
                                    f"POSE (IMAGE 3): Use the exact 3D skeletal posture and the '{angle_name}' camera angle.\n"
                                    f"OUTFIT: A high-quality {cloth_main}. {cloth_detail}.\n"
                                    f"ENVIRONMENT: {bg}. Professional lighting.\n"
                                    f"RESTRICTION: Japanese woman. Lips sealed, no teeth. 8k photorealistic."
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
                                    
                                    # 顔ブラーの適用
                                    final_img = apply_face_blur(raw_img) if enable_blur else raw_img
                                    
                                    st.image(final_img, caption=f"{angle_name} View", use_container_width=True)
                                    
                                    # ダウンロードボタン
                                    buf = io.BytesIO()
                                    final_img.save(buf, format="JPEG")
                                    st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"karinto_{i+1}.jpg", key=f"dl_{i}")
                                else:
                                    st.error("AIの判断により生成がスキップされました。")
                            except Exception as e:
                                st.error(f"エラーが発生しました: {e}")
                            
                            # 連続リクエストによる負荷軽減
                            time.sleep(1.2)
