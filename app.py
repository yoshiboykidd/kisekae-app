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

# --- 1. 背景・セッション初期化 ---
BG_OPTIONS = {
    "高級スイートルーム (温かい照明)": "Luxury hotel presidential suite with warm soft lighting",
    "大理石のホテルロビー (豪華なシャンデリア)": "Grand marble lobby of a 5-star hotel with elegant chandeliers",
    "都会の夜景 (キラキラしたボケ)": "Shimmering city night view of Tokyo with colorful bokeh lights",
    "陽光が差し込む明るいテラス (自然光)": "Sunny outdoor terrace with soft natural sunlight and greenery bokeh",
    "白を基調とした明るいリビング": "Bright minimalist luxury living room with white interior and soft morning light",
    "緑の見える午後の公園 (透明感)": "Beautiful park with lush green trees and soft afternoon sun, deep bokeh",
    "夜のインフィニティプール": "Luxury infinity pool at night with turquoise water reflections",
    "伝統的な和室 (行灯の光)": "Traditional Japanese room with tatami and soft paper lantern light"
}

if "generated_images" not in st.session_state:
    st.session_state.generated_images = [None] * 4
if "current_pose_paths" not in st.session_state:
    st.session_state.current_pose_paths = []
if "anchor_part" not in st.session_state:
    st.session_state.anchor_part = None

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

def generate_image(client, idx, path, identity_part, anchor_part, wardrobe_task, bg_prompt, enable_blur, cast_name):
    angle = path.split('_')[-1].split('.')[0]
    with open(path, "rb") as f:
        pose_part = types.Part.from_bytes(data=f.read(), mime_type='image/jpeg')
    
    prompt = (
        f"CRITICAL MANDATE: ABSOLUTE CONSISTENCY.\n"
        f"1. FACE IDENTITY (IMAGE 1): High-fidelity transplant of the face from IMAGE 1. 100% match.\n"
        f"2. ANATOMICAL MASS (IMAGE 1): Use EXACT physical body mass/weight/curves from IMAGE 1. IMAGE 3 is skeleton only.\n"
        f"3. WARDROBE (IMAGE 2): {wardrobe_task}\n"
        f"4. SCENE: {bg_prompt}, 85mm portrait bokeh, Japanese woman, lips sealed."
    )
    
    response = client.models.generate_content(
        model='gemini-3-pro-image-preview',
        contents=[identity_part, anchor_part, pose_part, prompt],
        config=types.GenerateContentConfig(response_modalities=['IMAGE'], image_config=types.ImageConfig(aspect_ratio="2:3"))
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
    st.title("🔐 Login ver 2.23")
    if st.text_input("合言葉", type="password") == "karin10" and st.button("ログイン"):
        st.session_state.password_correct = True; st.rerun()
    st.stop()

# --- 4. メインUI ---
st.title("📸 AI KISEKAE Manager ver 2.23")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

with st.sidebar:
    cast_name = st.text_input("👤 キャスト名", "cast")
    source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
    ref_img = st.file_uploader("衣装参考 (IMAGE 2 / 任意)", type=['png', 'jpg', 'jpeg'])
    cloth_main = st.selectbox("衣装カテゴリ", ["タイトミニドレス", "清楚ワンピース", "水着", "浴衣", "ナース服", "その他"])
    cloth_detail = st.text_input("衣装仕様書", placeholder="例：黒サテン、フリル付き")
    selected_bg_label = st.selectbox("背景を選択", list(BG_OPTIONS.keys()))
    bg_free_text = st.text_input("背景自由入力")
    pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
    enable_blur = st.checkbox("🛡️ 楕円顔ブラーを適用")
    
    st.divider()
    if st.button("✨ 4枚一括生成 (新規)") and source_img:
        st.session_state.current_pose_paths = get_4_preset_poses(pose_pattern)
        # アンカー確定
        if ref_img:
            st.session_state.anchor_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
        else:
            with st.spinner("衣装デザインを固定中..."):
                res = client.models.generate_content(model='gemini-3-pro-image-preview', contents=[f"Catalog photo of {cloth_main}, {cloth_detail}"])
                st.session_state.anchor_part = types.Part.from_bytes(data=res.candidates[0].content.parts[0].inline_data.data, mime_type='image/png')
        
        # 4枚生成実行
        final_bg = bg_free_text.strip() if bg_free_text.strip() else BG_OPTIONS[selected_bg_label]
        identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')
        wardrobe_task = f"Replicate IMAGE 2 design exactly. Specs: {cloth_detail}."
        
        for i, path in enumerate(st.session_state.current_pose_paths):
            st.session_state.generated_images[i] = generate_image(client, i, path, identity_part, st.session_state.anchor_part, wardrobe_task, final_bg, enable_blur, cast_name)
            time.sleep(1.2)

# --- 5. 表示と個別再生成 ---
if any(st.session_state.generated_images):
    st.subheader("🖼️ 生成結果")
    rows = [st.columns(2), st.columns(2)]
    placeholders = [rows[0][0], rows[0][1], rows[1][0], rows[1][1]]
    final_bg = bg_free_text.strip() if bg_free_text.strip() else BG_OPTIONS[selected_bg_label]
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')
    wardrobe_task = f"Replicate IMAGE 2 design exactly. Specs: {cloth_detail}."

    for i, img in enumerate(st.session_state.generated_images):
        if img:
            with placeholders[i]:
                angle = st.session_state.current_pose_paths[i].split('_')[-1].split('.')[0]
                st.image(img, caption=angle, use_container_width=True)
                
                # 個別ダウンロードボタン
                buf = io.BytesIO(); img.save(buf, format="JPEG")
                st.download_button(f"💾 {angle}を保存", buf.getvalue(), f"{cast_name}_{angle}.jpg", "image/jpeg", key=f"dl_{i}")
                
                # 個別再生成ボタン
                if st.button(f"🔄 {angle}を撮り直し", key=f"redo_{i}"):
                    with st.spinner(f"{angle}を再生成中..."):
                        new_img = generate_image(client, i, st.session_state.current_pose_paths[i], identity_part, st.session_state.anchor_part, wardrobe_task, final_bg, enable_blur, cast_name)
                        if new_img:
                            st.session_state.generated_images[i] = new_img
                            st.rerun()
