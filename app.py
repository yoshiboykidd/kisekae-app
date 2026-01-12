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

# --- 1. 背景リスト ---
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

# --- 2. ポーズ選出・顔ブラー・認証 (ver 2.20を継承) ---
def get_4_preset_poses(pattern):
    base_path = "presets/poses"
    stand_dir, sit_dir = os.path.join(base_path, "standing"), os.path.join(base_path, "sitting")
    def get_set_ids(d): return sorted(list(set(f.split('_')[0] + "_" + f.split('_')[1] for f in os.listdir(d)))) if os.path.exists(d) else []
    def find_file(d, sid, kws):
        if not os.path.exists(d): return None
        for f in os.listdir(d):
            if f.startswith(sid) and any(kw.lower() in f.lower() for kw in kws): return os.path.join(d, f)
        return None
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

def apply_face_blur(img, radius):
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').detectMultiScale(cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY), 1.05, 3)
    if len(faces) == 0: return img
    mask = Image.new('L', img.size, 0); draw = ImageDraw.Draw(mask)
    for (x, y, w, h) in faces: draw.ellipse([x-w*0.1, y-h*0.2, x+w*1.1, y+h*1.1], fill=255)
    return Image.composite(img.filter(ImageFilter.GaussianBlur(radius)), img, mask.filter(ImageFilter.GaussianBlur(radius/2)))

if "password_correct" not in st.session_state: st.session_state["password_correct"] = False
if not st.session_state["password_correct"]:
    st.title("🔐 Login ver 2.21")
    if st.text_input("合言葉", type="password") == "karin10" and st.button("ログイン"): st.session_state["password_correct"] = True; st.rerun()
    st.stop()

# --- 3. メインアプリ ---
st.title("📸 AI KISEKAE Manager ver 2.21")

with st.sidebar:
    cast_name = st.text_input("👤 キャスト名", "cast")
    source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
    ref_img = st.file_uploader("衣装参考 (IMAGE 2 / 任意)", type=['png', 'jpg', 'jpeg'])
    cloth_main = st.selectbox("衣装カテゴリ", ["タイトミニドレス", "清楚ワンピース", "水着", "浴衣", "ナース服", "その他"])
    cloth_detail = st.text_input("衣装仕様書", placeholder="例：黒サテン、フリル付き")
    selected_bg_label = st.selectbox("背景を選択", list(BG_OPTIONS.keys()))
    bg_free_text = st.text_input("背景自由入力")
    pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
    enable_blur = st.checkbox("🛡️ 楕円顔ブラー")
    run_button = st.button("✨ 掟を遵守して4枚一括生成")

if run_button and source_img:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    pose_paths = get_4_preset_poses(pose_pattern)
    
    if pose_paths:
        # --- アンカー生成ロジック ---
        final_style_part = None
        if ref_img:
            final_style_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            wardrobe_task = f"Strictly replicate the outfit in IMAGE 2. Specs: {cloth_detail}."
        else:
            with st.spinner("衣装アンカー固定中..."):
                anchor_res = client.models.generate_content(model='gemini-3-pro-image-preview', contents=[f"A catalog photo of {cloth_main}, {cloth_detail}"])
                final_style_part = types.Part.from_bytes(data=anchor_res.candidates[0].content.parts[0].inline_data.data, mime_type='image/png')
                wardrobe_task = f"Use the design from IMAGE 2 as the absolute master. Specs: {cloth_detail}."

        rows = [st.columns(2), st.columns(2)]; placeholders = [rows[0][0], rows[0][1], rows[1][0], rows[1][1]]
        final_bg = bg_free_text.strip() if bg_free_text.strip() else BG_OPTIONS[selected_bg_label]
        identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')

        for i, path in enumerate(pose_paths):
            angle = path.split('_')[-1].split('.')[0]
            with placeholders[i]:
                with st.spinner(f"{angle}..."):
                    with open(path, "rb") as f: pose_part = types.Part.from_bytes(data=f.read(), mime_type='image/jpeg')
                    
                    # --- プロンプト掟: アイデンティティ & 解剖学的固定 (ver 2.21) ---
                    prompt = (
                        f"CRITICAL MANDATE: ABSOLUTE CONSISTENCY REQUIRED.\n"
                        f"1. FACE IDENTITY (IMAGE 1): The face must be a 100% perfect match to IMAGE 1. Do not alter features, eye shape, or nose bridge for any angle. It is a high-fidelity transplant of IMAGE 1.\n"
                        f"2. ANATOMICAL MASS (IMAGE 1): The subject MUST have the EXACT physical body mass, bone structure, shoulder width, and waist-to-hip ratio as the woman in IMAGE 1. IMAGE 3 is an invisible ghost guide; IGNORE its body shape/thinness completely. Preserve the woman's curves and weight from IMAGE 1.\n"
                        f"3. WARDROBE (IMAGE 2): {wardrobe_task}\n"
                        f"4. SCENE: {final_bg}, professional 85mm portrait, shallow depth of field, Japanese woman, lips sealed."
                    )
                    
                    response = client.models.generate_content(
                        model='gemini-3-pro-image-preview',
                        contents=[identity_part, final_style_part, pose_part, prompt],
                        config=types.GenerateContentConfig(response_modalities=['IMAGE'], image_config=types.ImageConfig(aspect_ratio="2:3"))
                    )

                    if response.candidates and response.candidates[0].content.parts:
                        img_data = response.candidates[0].content.parts[0].inline_data.data
                        final_img = Image.open(io.BytesIO(img_data)).resize((600, 900))
                        if enable_blur: final_img = apply_face_blur(final_img, 30)
                        st.image(final_img, caption=angle, use_container_width=True)
                        buf = io.BytesIO(); final_img.save(buf, format="JPEG")
                        st.download_button(f"💾 {angle}", buf.getvalue(), f"{cast_name}_{angle}.jpg", "image/jpeg", key=f"dl_{i}")
                    time.sleep(1.5)
