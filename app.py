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

# --- 1. システム設定 (ver 2.60: Composition & Identity Focus) ---
VERSION = "2.60"
st.set_page_config(page_title=f"AI KISEKAE Manager v{VERSION}", layout="wide")

# セッション初期化 (既存の安定設定を継承)
for key in ["generated_images", "error_log", "anchor_part", "wardrobe_task", "current_pose_texts", "final_bg_prompt"]:
    if key not in st.session_state:
        if key == "generated_images": st.session_state[key] = [None] * 4
        elif key == "error_log": st.session_state[key] = []
        elif key in ["anchor_part", "wardrobe_task", "final_bg_prompt"]: st.session_state[key] = None
        else: st.session_state[key] = []

# 【ver 2.60 調整】顔の固定度を上げるためのポーズリスト（距離感を微調整）
STAND_PROMPTS = [
    "Knee-up portrait, standing naturally, hand touching hair, looking at camera, high facial detail",
    "Full body portrait, leaning slightly against a wall, elegant posture, maintaining 2.43 facial features",
    "Thigh-up shot, walking slowly, looking back over shoulder with precise facial identity",
    "Full body portrait, standing with weight on one leg, hand on hip, focused on 2.43 identity",
    "Knee-up portrait, standing by a railing, clear and sharp facial features of IMAGE 1"
]
SIT_PROMPTS = [
    "Knee-up sitting pose on a sofa, looking at camera with 100% facial match, gentle smile",
    "Thigh-up shot, sitting sideways on a chair, relaxed posture, high facial clarity",
    "Full body portrait, sitting gracefully on steps, hands in lap, maintaining 2.43 features",
    "Knee-up casual sitting pose, leaning back on hands, sharp focus on 2.43 face"
]

CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual everyday Japanese fashion", "back_prompt": "natural skin texture, morning sun, high-fidelity facial render"},
    "2. 水着（ビーチ）": {"en": "High-end stylish beachwear", "back_prompt": "healthy skin glow, vibrant summer lighting, sharp facial focus"},
    "3. 部屋着（リラックス）": {"en": "Soft lounge wear, silk or knit lingerie-style", "back_prompt": "warm rim lighting, soft beauty light on face, cinematic intimacy"},
    "4. オフィス（スーツ）": {"en": "Elegant business professional attire", "back_prompt": "sharp corporate lighting, professional look, high facial clarity"},
    "5. コスチューム": {"en": "High-quality themed costume", "back_prompt": "meticulous details, professional strobe, flawless facial identity"},
    "6. 夜の装い（ドレス）": {"en": "Sophisticated evening gown", "back_prompt": "luxury bokeh, dramatic lighting on 2.43 face, glamorous sheen"}
}

# --- 2. ユーティリティ ---
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
    """【絶対ルール：ver 2.54 黄金律を再強化】構図(遠近)による顔崩れを防止"""
    cat_info = CATEGORIES[cat_key]
    prompt = (
        f"STRICT PHYSICAL FIDELITY: ABSOLUTE IDENTITY LOCK.\n"
        f"1. FACE FIDELITY (IMAGE 1): Replicate the EXACT facial features, eye shape, and bone structure of the woman in IMAGE 1. 100% identity match is mandatory.\n"
        f"2. BODY FIDELITY (IMAGE 1): [FIXED_IDENTITY] Replicate the exact body mass, curves, and weight. Do not change her proportions.\n"
        f"3. POSE & COMPOSITION: {pose_text}. Use 85mm portrait lens to ensure no facial distortion.\n"
        f"4. WARDROBE (IMAGE 2): {wardrobe_task}\n"
        f"5. RENDER: {bg_prompt}, {cat_info['back_prompt']}, professional lighting, 8k, photorealistic, lips sealed."
    )
    res_data = generate_with_retry(client, [identity_part, anchor_part], prompt)
    if isinstance(res_data, bytes):
        img = Image.open(io.BytesIO(res_data)).resize((600, 900))
        return apply_face_blur(img) if enable_blur else img
    return res_data

# --- 3. UI 構築 ---
if not st.session_state.get("password_correct", False):
    st.title(f"🔐 Login ver {VERSION}")
    if st.text_input("合言葉", type="password") == "karin10" and st.button("ログイン"):
        st.session_state.password_correct = True; st.rerun()
    st.stop()

st.title(f"📸 AI KISEKAE Manager ver {VERSION}")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

with st.sidebar:
    st.header("🛠 Control Panel")
    cast_name = st.text_input("👤 キャスト名", "cast")
    source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
    if source_img:
        st.image(source_img, caption="ターゲット・アイデンティティ (2.43)", use_container_width=True)
    ref_img = st.file_uploader("衣装参考 (IMAGE 2 / 任意)", type=['png', 'jpg', 'jpeg'])
    if ref_img:
        st.image(ref_img, caption="衣装設計図", use_container_width=True)
    st.divider()
    cloth_main = st.selectbox("衣装カテゴリ", list(CATEGORIES.keys()))
    cloth_detail = st.text_input("衣装仕様書", placeholder="例：黒サテン、フリル付き")
    st.divider()
    bg_text = st.text_input("場所", "高級ホテルの部屋")
    time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "warm sunset glow", "夜 (Night)": "night lights"}
    time_of_day = st.radio("時間帯", list(time_mods.keys()), index=0)
    pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
    enable_blur = st.checkbox("🛡️ 楕円顔ブラー")
    run_btn = st.button("✨ 4枚一括生成")

identity_part = None
if source_img:
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')

# --- 4. 生成実行 (進捗バー) ---
if run_btn and source_img:
    st.session_state.error_log = []
    st.session_state.generated_images = [None] * 4
    st.session_state.final_bg_prompt = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh"
    
    if pose_pattern == "立ち3:座り1":
        poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
    else:
        poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
    random.shuffle(poses)
    st.session_state.current_pose_texts = poses

    status_container = st.empty()
    progress_bar = st.progress(0)

    # ステップ1: アンカー
    with status_container.container():
        st.info("🕒 ステップ 1/2: 衣装設計図（アンカー）を構築中...")
        anchor_prompt = f"Studio catalog photo of the {CATEGORIES[cloth_main]['en']}. Specs: {cloth_detail}. Isolated view."
        contents = [types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')] if ref_img else []
        res_data = generate_with_retry(client, contents, anchor_prompt)
        if isinstance(res_data, bytes):
            st.session_state.anchor_part = types.Part.from_bytes(data=res_data, mime_type='image/png')
            st.session_state.wardrobe_task = f"Strictly replicate the clothing from IMAGE 2. {cloth_detail}."
        else:
            st.error(f"❌ アンカー生成失敗: {res_data}"); st.stop()

    # ステップ2: 4枚生成
    for i, p_txt in enumerate(st.session_state.current_pose_texts):
        current_step = i + 1
        with status_container.container():
            st.info(f"🎨 ステップ 2/2: 顔の同一性を固定して生成中 ({current_step}/4)...")
        
        img_res = generate_image_by_text(client, p_txt, identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur, cloth_main)
        if isinstance(img_res, Image.Image):
            st.session_state.generated_images[i] = img_res
        else:
            st.session_state.error_log.append(f"{current_step}枚目: {img_res}")
        
        progress_bar.progress(current_step / 4)
        time.sleep(1)

    status_container.success("✨ 生成完了！")
    time.sleep(0.5)
    status_container.empty()
    st.rerun()

# --- 5. 表示エリア ---
if st.session_state.error_log:
    for err in st.session_state.error_log: st.warning(err)

if any(st.session_state.generated_images):
    st.subheader(f"🖼️ 生成結果 (ver {VERSION})")
    cols = st.columns(2)
    for i, img in enumerate(st.session_state.generated_images):
        if img:
            with cols[i % 2]:
                st.image(img, use_container_width=True)
                c1, c2 = st.columns(2)
                with c1:
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"img_{i}.jpg", "image/jpeg", key=f"dl_{i}")
                with c2:
                    if st.button(f"🔄 撮り直し #{i}", key=f"re_{i}"):
                        if identity_part and st.session_state.anchor_part:
                            with st.spinner("再生成中..."):
                                res = generate_image_by_text(client, st.session_state.current_pose_texts[i], identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur, cloth_main)
                                if isinstance(res, Image.Image):
                                    st.session_state.generated_images[i] = res; st.rerun()
                                else: st.error(f"再生成失敗: {res}")
