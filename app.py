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

# --- 1. セッション初期化 ---
if "generated_images" not in st.session_state:
    st.session_state.generated_images = [None] * 4
if "current_pose_paths" not in st.session_state:
    st.session_state.current_pose_paths = []
if "anchor_part" not in st.session_state:
    st.session_state.anchor_part = None
if "wardrobe_task" not in st.session_state:
    st.session_state.wardrobe_task = ""
if "final_bg_prompt" not in st.session_state:
    st.session_state.final_bg_prompt = ""

# --- 2. ユーティリティ関数 ---
def get_set_ids(directory):
    if not os.path.exists(directory): return []
    ids = []
    for f in os.listdir(directory):
        if not f.startswith('.') and '_' in f:
            parts = f.split('_')
            if len(parts) >= 2: ids.append(parts[0] + "_" + parts[1])
    return sorted(list(set(ids)))

def find_file(directory, set_id, keywords):
    if not os.path.exists(directory): return None
    for f in os.listdir(directory):
        if f.startswith(set_id) and any(kw.lower() in f.lower() for kw in keywords):
            return os.path.join(directory, f)
    return None

def get_4_preset_poses(pattern):
    base_path = "presets/poses"
    stand_dir, sit_dir = os.path.join(base_path, "standing"), os.path.join(base_path, "sitting")
    s_sets, t_sets = get_set_ids(stand_dir), get_set_ids(sit_dir)
    res = []
    try:
        if pattern == "立ち3:座り1":
            s = random.sample(s_sets, 3); t = random.sample(t_sets, 1)
            res = [find_file(stand_dir, s[0], ["Front", "Frot"]), find_file(stand_dir, s[1], ["Quarter"]), find_file(stand_dir, s[2], ["Low"]), find_file(sit_dir, t[0], ["High"])]
        else:
            s = random.sample(s_sets, 2); t = random.sample(t_sets, 2)
            res = [find_file(stand_dir, s[0], ["Front", "Frot"]), find_file(stand_dir, s[1], ["Low"]), find_file(sit_dir, t[0], ["Quarter"]), find_file(sit_dir, t[1], ["High"])]
    except: return []
    return [r for r in res if r]

def generate_image(client, path, identity_part, anchor_part, wardrobe_task, bg_prompt, enable_blur):
    angle = path.split('_')[-1].split('.')[0]
    with open(path, "rb") as f:
        pose_part = types.Part.from_bytes(data=f.read(), mime_type='image/jpeg')
    
    prompt = (
        f"CRITICAL MANDATE: ABSOLUTE CONSISTENCY.\n"
        f"1. FACE IDENTITY (IMAGE 1): High-fidelity transplant of the face from IMAGE 1. 100% match.\n"
        f"2. ANATOMICAL MASS (IMAGE 1): Use EXACT physical body mass/weight/curves from IMAGE 1. IMAGE 3 is skeleton only.\n"
        f"3. WARDROBE (IMAGE 2): {wardrobe_task}\n"
        f"4. SCENE: {bg_prompt}, professional 85mm portrait, shallow depth of field, Japanese woman, lips sealed."
    )
    
    response = client.models.generate_content(
        model='gemini-3-pro-image-preview',
        contents=[identity_part, anchor_part, pose_part, prompt],
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE'],
            safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')],
            image_config=types.ImageConfig(aspect_ratio="2:3")
        )
    )

    if response.candidates and response.candidates[0].content.parts:
        img_data = response.candidates[0].content.parts[0].inline_data.data
        img = Image.open(io.BytesIO(img_data)).resize((600, 900))
        if enable_blur:
            cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').detectMultiScale(cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY), 1.05, 3)
            if len(faces) > 0:
                mask = Image.new('L', img.size, 0); draw = ImageDraw.Draw(mask)
                for (x, y, w, h) in faces: draw.ellipse([x-w*0.1, y-h*0.2, x+w*1.1, y+h*1.1], fill=255)
                img = Image.composite(img.filter(ImageFilter.GaussianBlur(30)), img, mask.filter(ImageFilter.GaussianBlur(15)))
        return img
    return None

# --- 3. 認証 ---
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if not st.session_state.password_correct:
    st.title("🔐 Login ver 2.29")
    if st.text_input("合言葉", type="password") == "karin10" and st.button("ログイン"):
        st.session_state.password_correct = True; st.rerun()
    st.stop()

# --- 4. メインUI ---
st.title("📸 AI KISEKAE Manager ver 2.29")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

with st.sidebar:
    cast_name = st.text_input("👤 キャスト名", "cast")
    source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
    if source_img: st.image(source_img, caption="キャストプレビュー", use_container_width=True)
    
    ref_img = st.file_uploader("衣装参考 (IMAGE 2 / 任意)", type=['png', 'jpg', 'jpeg'])
    if ref_img: st.image(ref_img, caption="衣装参考プレビュー", use_container_width=True)
            
    st.divider()
    cloth_main = st.selectbox("衣装カテゴリ", ["タイトミニドレス", "清楚ワンピース", "水着", "浴衣", "ナース服", "その他"])
    cloth_detail = st.text_input("衣装仕様書", placeholder="例：黒サテン、フリル付き")
    
    st.divider()
    st.subheader("🌅 背景・時間帯")
    bg_text = st.text_input("場所を自由入力", "高級ホテルの部屋")
    time_of_day = st.radio("時間帯", ["昼 (Daylight)", "夕方 (Golden Hour)", "夜 (Night)"], index=0)
    
    st.divider()
    pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
    enable_blur = st.checkbox("🛡️ 楕円顔ブラー")
    
    run_btn = st.button("✨ 4枚一括生成 (新規)")

# --- 5. 生成ロジック (新・アンカー生成) ---
if run_btn and source_img:
    st.session_state.generated_images = [None] * 4
    st.session_state.anchor_part = None
    
    # 時間帯プロンプト設定
    time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "warm sunset glow", "夜 (Night)": "night lights"}
    st.session_state.final_bg_prompt = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh background"

    # --- フェーズ1: 衣装アンカーの再構築 ---
    with st.spinner("衣装の『設計図』を再構築中..."):
        try:
            if ref_img:
                # 参考画像がある場合：画像を元に「服だけ」を再生成
                ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
                anchor_prompt = f"Create a high-quality studio catalog photograph of the EXACT SAME outfit shown in the image. Focus only on the garment. Specs: {cloth_detail}. Isolated front view."
                res = client.models.generate_content(
                    model='gemini-3-pro-image-preview', 
                    contents=[ref_part, anchor_prompt],
                    config=types.GenerateContentConfig(response_modalities=['IMAGE'], image_config=types.ImageConfig(aspect_ratio="1:1"))
                )
            else:
                # 参考画像がない場合：テキストから生成
                anchor_prompt = f"A professional catalog photograph of a {cloth_main}. {cloth_detail}. Clear front view, fabric texture."
                res = client.models.generate_content(
                    model='gemini-3-pro-image-preview', 
                    contents=[anchor_prompt],
                    config=types.GenerateContentConfig(response_modalities=['IMAGE'], image_config=types.ImageConfig(aspect_ratio="1:1"))
                )
            
            if res.candidates and res.candidates[0].content.parts:
                st.session_state.anchor_part = types.Part.from_bytes(data=res.candidates[0].content.parts[0].inline_data.data, mime_type='image/png')
                st.session_state.wardrobe_task = f"Use the design from IMAGE 2 (Anchor) as the absolute master. Specs: {cloth_detail}."
            else: st.error("設計図の生成に失敗しました"); st.stop()
        except Exception as e: st.error(f"Error: {e}"); st.stop()

    # --- フェーズ2: 4枚生成 ---
    st.session_state.current_pose_paths = get_4_preset_poses(pose_pattern)
    progress_bar = st.progress(0)
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')

    for i, path in enumerate(st.session_state.current_pose_paths):
        img = generate_image(client, path, identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur)
        if img: st.session_state.generated_images[i] = img
        progress_bar.progress((i + 1) / 4)
    progress_bar.empty()
    st.rerun()

# --- 6. 結果表示エリア ---
if any(st.session_state.generated_images):
    st.subheader("🖼️ 生成結果")
    cols = st.columns(2)
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg') if source_img else None

    for i, img in enumerate(st.session_state.generated_images):
        if img:
            with cols[i % 2]:
                angle = st.session_state.current_pose_paths[i].split('_')[-1].split('.')[0] if i < len(st.session_state.current_pose_paths) else "Photo"
                st.image(img, caption=angle, use_container_width=True)
                c1, c2 = st.columns(2)
                with c1:
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button(f"💾 保存", buf.getvalue(), f"{cast_name}_{angle}.jpg", "image/jpeg", key=f"dl_{i}")
                with c2:
                    if st.button(f"🔄 撮り直し", key=f"redo_{i}"):
                        if identity_part:
                            with st.spinner(f"撮り直し中..."):
                                new_img = generate_image(client, st.session_state.current_pose_paths[i], identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur)
                                if new_img:
                                    st.session_state.generated_images[i] = new_img
                                    st.rerun()
