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
if "anchor_part" not in st.session_state:
    st.session_state.anchor_part = None
if "wardrobe_task" not in st.session_state:
    st.session_state.wardrobe_task = ""
if "final_bg_prompt" not in st.session_state:
    st.session_state.final_bg_prompt = ""

# ver 2.4 用のポーズ指示テキスト
POSE_DESCRIPTIONS = [
    "Full body, standing, facing front, looking at camera",
    "Full body, 45 degree angle, elegant standing pose",
    "Full body, sitting gracefully on a chair or sofa",
    "Full body, looking over shoulder, back view angle"
]

# --- 2. ユーティリティ関数 ---
def apply_face_blur(img, radius=30):
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').detectMultiScale(cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY), 1.05, 3)
    if len(faces) == 0: return img
    mask = Image.new('L', img.size, 0); draw = ImageDraw.Draw(mask)
    for (x, y, w, h) in faces: 
        draw.ellipse([x-w*0.1, y-h*0.2, x+w*1.1, y+h*1.1], fill=255)
    return Image.composite(img.filter(ImageFilter.GaussianBlur(radius)), img, mask.filter(ImageFilter.GaussianBlur(radius/2)))

def generate_image_no_ref(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, enable_blur):
    """ポーズ画像を参照せず、テキスト指示で生成する (ver 2.4)"""
    
    prompt = (
        f"STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK.\n"
        f"1. PHYSICAL IDENTITY (IMAGE 1): Replicate the EXACT body mass, curves, weight, and shoulder width of the woman in IMAGE 1. Do not make her thinner. 100% anatomical match.\n"
        f"2. POSE: {pose_text}.\n"
        f"3. FACE (IMAGE 1): Precise facial identity match. Identical features.\n"
        f"4. WARDROBE (IMAGE 2): {wardrobe_task}\n"
        f"5. SCENE: {bg_prompt}, 85mm portrait, professional lighting, Japanese woman, lips sealed."
    )
    
    response = client.models.generate_content(
        model='gemini-3-pro-image-preview',
        contents=[identity_part, anchor_part, prompt],
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE'],
            safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')],
            image_config=types.ImageConfig(aspect_ratio="2:3")
        )
    )

    if response.candidates and response.candidates[0].content.parts:
        img_data = response.candidates[0].content.parts[0].inline_data.data
        img = Image.open(io.BytesIO(img_data)).resize((600, 900))
        if enable_blur: img = apply_face_blur(img)
        return img
    return None

# --- 3. 認証・UI ---
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if not st.session_state.password_correct:
    st.title("🔐 Login ver 2.4")
    if st.text_input("合言葉", type="password") == "karin10" and st.button("ログイン"):
        st.session_state.password_correct = True; st.rerun()
    st.stop()

st.title("📸 AI KISEKAE Manager ver 2.4")
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
    enable_blur = st.checkbox("🛡️ 楕円顔ブラー")
    run_btn = st.button("✨ 4枚一括生成")

# --- 4. 生成実行ロジック ---
if run_btn and source_img:
    st.session_state.generated_images = [None] * 4
    
    time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "warm sunset glow", "夜 (Night)": "night lights"}
    st.session_state.final_bg_prompt = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh background"

    with st.spinner("衣装の設計図を再構築中..."):
        try:
            if ref_img:
                ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
                anchor_prompt = f"Professional studio catalog photograph of the EXACT SAME outfit in image. Specs: {cloth_detail}. Isolated front view."
                res = client.models.generate_content(model='gemini-3-pro-image-preview', contents=[ref_part, anchor_prompt], config=types.GenerateContentConfig(response_modalities=['IMAGE'], image_config=types.ImageConfig(aspect_ratio="1:1")))
            else:
                anchor_prompt = f"Professional catalog photograph of {cloth_main}. {cloth_detail}."
                res = client.models.generate_content(model='gemini-3-pro-image-preview', contents=[anchor_prompt], config=types.GenerateContentConfig(response_modalities=['IMAGE'], image_config=types.ImageConfig(aspect_ratio="1:1")))
            
            if res.candidates and res.candidates[0].content.parts:
                st.session_state.anchor_part = types.Part.from_bytes(data=res.candidates[0].content.parts[0].inline_data.data, mime_type='image/png')
                st.session_state.wardrobe_task = f"Replicate outfit from IMAGE 2 exactly. Specs: {cloth_detail}."
            else: st.stop()
        except Exception as e: st.error(f"Error: {e}"); st.stop()

    progress_bar = st.progress(0)
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')

    for i, pose_txt in enumerate(POSE_DESCRIPTIONS):
        img = generate_image_no_ref(client, pose_txt, identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur)
        if img:
            st.session_state.generated_images[i] = img
        progress_bar.progress((i + 1) / 4)
    progress_bar.empty()
    st.rerun()

# --- 5. 表示 ---
if any(st.session_state.generated_images):
    st.subheader("🖼️ 生成結果 (ポーズ画像なし)")
    cols = st.columns(2)
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg') if source_img else None
    
    # ラベル用
    angle_names = ["正面", "斜め", "座り", "振り向き"]

    for i, img in enumerate(st.session_state.generated_images):
        if img:
            with cols[i % 2]:
                st.image(img, caption=angle_names[i], use_container_width=True)
                c1, c2 = st.columns(2)
                with c1:
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button(f"💾 {angle_names[i]}を保存", buf.getvalue(), f"{cast_name}_{angle_names[i]}.jpg", "image/jpeg", key=f"dl_{i}")
                with c2:
                    if st.button(f"🔄 撮り直し", key=f"redo_{i}"):
                        if identity_part:
                            with st.spinner(f"撮り直し中..."):
                                new_img = generate_image_no_ref(client, POSE_DESCRIPTIONS[i], identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur)
                                if new_img: st.session_state.generated_images[i] = new_img; st.rerun()
