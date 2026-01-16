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

# --- 1. システム設定 (ver 2.66: Ultimate Identity Lock) ---
VERSION = "2.66"
st.set_page_config(page_title=f"AI KISEKAE Manager v{VERSION}", layout="wide")

# セッション状態の初期化
for key in ["generated_images", "error_log", "anchor_part", "wardrobe_task", "current_pose_texts", "final_bg_prompt"]:
    if key not in st.session_state:
        if key == "generated_images": st.session_state[key] = [None] * 4
        elif key == "error_log": st.session_state[key] = []
        elif key in ["anchor_part", "wardrobe_task", "final_bg_prompt"]: st.session_state[key] = None
        else: st.session_state[key] = []

# --- 黄金律に基づく安全なポーズプール ---
STAND_PROMPTS = [
    "Full body portrait, standing naturally, hand gently touching hair, looking away, candid style",
    "Full body portrait, leaning against a wall, arms casually crossed, natural expression",
    "Full body portrait, walking slowly, looking back over shoulder, gentle look",
    "Full body portrait, standing with weight on one leg, one hand on hip",
    "Full body portrait, standing by a railing, looking out thoughtfully",
    "Full body portrait, standing with hands behind back, looking at camera",
    "Full body portrait, leaning forward slightly towards camera, hands on knees"
]
SIT_PROMPTS = [
    "Full body portrait, relaxed sitting pose on a sofa, looking at camera",
    "Full body portrait, sitting sideways on a chair, leaning on the backrest",
    "Full body portrait, sitting gracefully on steps, hands resting in lap",
    "Full body portrait, casual sitting pose on a plush surface, leaning back on hands",
    "Full body portrait, sitting on the edge of a bed, looking over shoulder"
]

# 6つの固定カテゴリー定義 (顔面描写への干渉を最小化)
CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual everyday Japanese fashion", "back_prompt": "natural soft skin, soft daylight, clear facial features"},
    "2. 水着（リゾート）": {"en": "High-end stylish resort swimwear", "back_prompt": "healthy skin glow, vibrant summer lighting, sharp facial focus"},
    "3. 部屋着（リラックス）": {"en": "Elegant silk night-fashion, satin camisole-style", "back_prompt": "ultra-soft focus, warm rim lighting, soft beauty face light"},
    "4. オフィス（スーツ）": {"en": "Elegant business professional attire", "back_prompt": "sharp corporate lighting, professional studio look, high facial clarity"},
    "5. コスチューム": {"en": "High-quality themed costume, professional uniform", "back_prompt": "meticulous details, professional strobe, flawless skin render"},
    "6. 夜の装い（ドレス）": {"en": "Sophisticated evening gown", "back_prompt": "luxury bokeh, dramatic lighting, soft facial fill-light"}
}

# --- 2. ユーティリティ & ロジック ---
def apply_face_blur(img, radius=30):
    try:
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').detectMultiScale(cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY), 1.05, 3)
        if len(faces) == 0: return img
        mask = Image.new('L', img.size, 0); draw = ImageDraw.Draw(mask)
        for (x, y, w, h) in faces: 
            draw.ellipse([x-w*0.1, y-h*0.2, x+w*1.1, y+h*1.1], fill=255)
        return Image.composite(img.filter(ImageFilter.GaussianBlur(radius)), img, mask.filter(ImageFilter.GaussianBlur(radius/2)))
    except: return img

def generate_with_retry(client, contents, prompt, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
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
                return response.candidates[0].content.parts[0].inline_data.data
            else: return "SAFETY_BLOCK"
        except Exception as e:
            if "503" in str(e) and attempt < max_retries:
                time.sleep(2); continue
            return str(e)
    return "RETRY_FAILED"

def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, enable_blur, cat_key):
    """【絶対ルール：ver 2.66】アイデンティティの『完全一致』を再定義"""
    cat_info = CATEGORIES[cat_key]
    prompt = (
        f"CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK.\n"
        f"1. FACE FIDELITY (IMAGE 1): Replicate the EXACT facial structure, eyes, and nose of the woman in IMAGE 1. 100% pixel-perfect identity match. Do not stylize or alter her features.\n"
        f"2. PHYSICAL IDENTITY (IMAGE 1): [FIXED_IDENTITY] Match the exact body mass, curves, and weight of IMAGE 1.\n"
        f"3. POSE & COMPOSITION: {pose_text}. Use an 85mm lens to ensure zero facial distortion.\n"
        f"4. WARDROBE (IMAGE 2): {wardrobe_task}\n"
        f"5. RENDER: {bg_prompt}, {cat_info['back_prompt']}, cinematic lighting with soft facial fill-light, 8k, lips sealed, neutral expression."
    )
    res_data = generate_with_retry(client, [identity_part, anchor_part], prompt)
    if isinstance(res_data, bytes):
        img = Image.open(io.BytesIO(res_data)).resize((600, 900))
        return apply_face_blur(img) if enable_blur else img
    return res_data

# --- 3. UI 構築 ---
st.title(f"📸 AI KISEKAE Manager ver {VERSION}")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

with st.sidebar:
    st.header("🛠 Control Panel")
    source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
    if source_img: st.image(source_img, caption="ターゲット", use_container_width=True)
    ref_img = st.file_uploader("衣装参考 (IMAGE 2 / 任意)", type=['png', 'jpg', 'jpeg'])
    if ref_img: st.image(ref_img, caption="リファレンス", use_container_width=True)
    st.divider()
    cloth_main = st.selectbox("衣装カテゴリー", list(CATEGORIES.keys()))
    cloth_detail = st.text_input("衣装仕様書", placeholder="例：サテンの光沢、シルクの質感")
    st.divider()
    bg_text = st.text_input("場所", "高級ホテルの部屋")
    time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "warm sunset glow", "夜 (Night)": "night lights"}
    time_of_day = st.radio("時間帯", list(time_mods.keys()), index=0)
    pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
    enable_blur = st.checkbox("🛡️ 楕円顔ブラー")
    run_btn = st.button("✨ 4枚一括生成")

# 撮り直し/再生成用の identity_part (ボタン外で定義)
identity_part = None
if source_img:
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')

# --- 4. 生成実行 ---
if run_btn and source_img:
    st.session_state.error_log = []
    st.session_state.generated_images = [None] * 4
    st.session_state.final_bg_prompt = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh"
    
    if pose_pattern == "立ち3:座り1":
        poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
    else:
        poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
    random.shuffle(poses); st.session_state.current_pose_texts = poses

    status_container = st.empty()
    progress_bar = st.progress(0)

    # ステップ1: アンカー
    with status_container.container():
        st.info("🕒 ステップ 1/2: 衣装設計図（アンカー）を構築中...")
        anchor_prompt = f"Professional studio product shot of {CATEGORIES[cloth_main]['en']}. Specs: {cloth_detail}. Isolated view."
        contents = [types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')] if ref_img else []
        res_data = generate_with_retry(client, contents, anchor_prompt)
        if isinstance(res_data, bytes):
            st.session_state.anchor_part = types.Part.from_bytes(data=res_data, mime_type='image/png')
            st.session_state.wardrobe_task = f"Strictly replicate the fashion design from IMAGE 2. {cloth_detail}."
        else:
            st.error(f"アンカー失敗: {res_data}"); st.stop()

    # ステップ2: 4枚生成
    for i, p_txt in enumerate(st.session_state.current_pose_texts):
        with status_container.container(): st.info(f"🎨 ステップ 2/2: 顔面固定ブースト実行中 ({i+1}/4)...")
        img_res = generate_image_by_text(client, p_txt, identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur, cloth_main)
        if isinstance(img_res, Image.Image): st.session_state.generated_images[i] = img_res
        else: st.session_state.error_log.append(f"{i+1}枚目: {img_res}")
        progress_bar.progress((i+1)/4); time.sleep(1)

    status_container.success("✨ 生成完了！"); time.sleep(0.5); status_container.empty(); st.rerun()

# --- 5. 表示エリア ---
if st.session_state.error_log:
    with st.expander("⚠️ 生成エラーの記録", expanded=True):
        for err in st.session_state.error_log: st.warning(err)

st.subheader(f"🖼️ 生成結果 (ver {VERSION})")
cols = st.columns(2)
for i in range(4):
    with cols[i % 2]:
        img = st.session_state.generated_images[i]
        if img:
            st.image(img, use_container_width=True)
            c1, c2 = st.columns(2)
            with c1:
                buf = io.BytesIO(); img.save(buf, format="JPEG")
                st.download_button("💾 保存", buf.getvalue(), f"img_{i}.jpg", "image/jpeg", key=f"dl_{i}")
            with c2:
                if st.button(f"🔄 撮り直し", key=f"re_{i}"):
                    if identity_part and st.session_state.anchor_part:
                        with st.spinner("再生成中..."):
                            res = generate_image_by_text(client, st.session_state.current_pose_texts[i], identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur, cloth_main)
                            if isinstance(res, Image.Image): st.session_state.generated_images[i] = res; st.rerun()
                            else: st.error(f"失敗: {res}")
        else:
            st.info(f"🔳 スロット {i+1}: 生成失敗")
            if st.button(f"⚡ 再送する", key=f"retry_{i}", type="primary"):
                if identity_part and st.session_state.anchor_part:
                    with st.spinner("再送中..."):
                        res = generate_image_by_text(client, st.session_state.current_pose_texts[i], identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur, cloth_main)
                        if isinstance(res, Image.Image): st.session_state.generated_images[i] = res; st.rerun()
