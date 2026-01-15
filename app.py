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

# --- 1. システム設定 (ver 2.56: Face Identity Rollback) ---
VERSION = "2.56"
st.set_page_config(page_title=f"AI KISEKAE Manager v{VERSION}", layout="wide")

# セッション状態の初期化
for key in ["generated_images", "error_log", "anchor_part", "wardrobe_task", "current_pose_texts", "final_bg_prompt"]:
    if key not in st.session_state:
        if key == "generated_images": st.session_state[key] = [None] * 4
        elif key == "error_log": st.session_state[key] = []
        elif key in ["anchor_part", "wardrobe_task", "final_bg_prompt"]: st.session_state[key] = None
        else: st.session_state[key] = []

# ポーズ定義 (2.43 黄金律を100%継承)
STAND_PROMPTS = [
    "Full body portrait, standing naturally with a relaxed posture, hand gently touching hair, looking slightly away from camera, candid style",
    "Full body portrait, leaning slightly against a wall or pillar, arms casually crossed, soft natural smile, angled body position",
    "Full body portrait, captured mid-movement like slowly walking, looking back over shoulder with a gentle expression",
    "Full body portrait, a dynamic pose standing with weight on one leg, one hand resting on hip, confident and relaxed look",
    "Full body portrait, standing by a railing or window, looking out with a thoughtful expression, soft side lighting"
]
SIT_PROMPTS = [
    "Full body portrait, relaxed sitting pose on a sofa or soft chair, one leg tucked naturally, looking at camera with a gentle smile",
    "Full body portrait, sitting sideways on a chair, leaning slightly on the backrest, relaxed and engaging posture",
    "Full body portrait, sitting gracefully on steps or a low stool, hands resting naturally in lap, looking slightly off-camera",
    "Full body portrait, a casual sitting pose on a plush surface, leaning back slightly on hands, comfortable atmosphere"
]

# 6つの固定カテゴリー
CATEGORIES = {
    "1. 私服（日常）": "Casual everyday Japanese fashion",
    "2. 水着（ビーチ）": "High-end stylish beachwear",
    "3. 部屋着（リラックス）": "Soft lounge wear, silk or knit lingerie-style",
    "4. オフィス（スーツ）": "Elegant business professional attire",
    "5. コスチューム": "High-quality themed costume, professional uniform",
    "6. 夜の装い（ドレス）": "Sophisticated evening gown, glamorous cocktail fashion"
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

def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, enable_blur):
    """【絶対ルール遵守】ver 2.43 のプロンプト構造を復元"""
    prompt = (
        f"STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK.\n"
        f"1. PHYSICAL IDENTITY (IMAGE 1): Replicate the EXACT body mass, curves, weight, and shoulder width of the woman in IMAGE 1. Do not make her thinner. 100% anatomical match.\n"
        f"2. POSE & COMPOSITION: {pose_text}. The composition must be a natural, candid-style portrait. Avoid stiff, posed, or 'mugshot-like' frontal stances. Capture a relaxed and engaging moment.\n"
        f"3. FACE (IMAGE 1): Precise facial identity match. Identical features from IMAGE 1.\n"
        f"4. WARDROBE (IMAGE 2): {wardrobe_task}\n"
        f"5. SCENE: {bg_prompt}, 85mm portrait, professional lighting, Japanese woman, lips sealed."
    )
    res_data = generate_with_retry(client, [identity_part, anchor_part], prompt)
    if isinstance(res_data, bytes):
        img = Image.open(io.BytesIO(res_data)).resize((600, 900))
        return apply_face_blur(img) if enable_blur else img
    return res_data

# --- 3. UI 構築 (サムネイル表示の修正) ---
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
    
    # 【UI修正】アップロード後の画像を表示
    source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
    if source_img:
        st.image(source_img, caption="2.43 黄金律ソース", use_container_width=True)
    
    ref_img = st.file_uploader("衣装参考 (IMAGE 2 / 任意)", type=['png', 'jpg', 'jpeg'])
    if ref_img:
        st.image(ref_img, caption="衣装設計図リファレンス", use_container_width=True)
        
    st.divider()
    cloth_main = st.selectbox("衣装カテゴリ", list(CATEGORIES.keys()))
    cloth_detail = st.text_input("衣装仕様書", placeholder="例：黒サテン、フリル付き")
    
    st.divider()
    st.subheader("🌅 背景・時間帯")
    bg_text = st.text_input("場所", "高級ホテルの部屋")
    time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "warm sunset glow", "夜 (Night)": "night lights"}
    time_of_day = st.radio("時間帯", list(time_mods.keys()), index=0)
    pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
    enable_blur = st.checkbox("🛡️ 楕円顔ブラー")
    run_btn = st.button("✨ 4枚一括生成")

# identity_partの定義 (撮り直し用)
identity_part = None
if source_img:
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')

# --- 4. 生成実行 ---
if run_btn and source_img:
    st.session_state.error_log = []
    st.session_state.generated_images = [None] * 4
    st.session_state.final_bg_prompt = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh background"
    
    if pose_pattern == "立ち3:座り1":
        poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
    else:
        poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
    random.shuffle(poses)
    st.session_state.current_pose_texts = poses

    with st.spinner("衣装の設計図（アンカー）を構築中..."):
        cat_en = CATEGORIES[cloth_main]
        if ref_img:
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            anchor_prompt = f"Studio catalog photo of the EXACT SAME {cat_en}. Specs: {cloth_detail}. Isolated view."
            res_data = generate_with_retry(client, [ref_part], anchor_prompt)
        else:
            anchor_prompt = f"Professional catalog photo of {cat_en}. {cloth_detail}."
            res_data = generate_with_retry(client, [], anchor_prompt)
        
        if isinstance(res_data, bytes):
            st.session_state.anchor_part = types.Part.from_bytes(data=res_data, mime_type='image/png')
            st.session_state.wardrobe_task = f"Replicate IMAGE 2 exactly. Specs: {cloth_detail}."
        else:
            st.error(f"アンカー生成失敗: {res_data}"); st.stop()

    p_bar = st.progress(0)
    for i, p_txt in enumerate(st.session_state.current_pose_texts):
        img_res = generate_image_by_text(client, p_txt, identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur)
        if isinstance(img_res, Image.Image): st.session_state.generated_images[i] = img_res
        else: st.session_state.error_log.append(f"{i+1}枚目: {img_res}")
        p_bar.progress((i + 1) / 4); time.sleep(1)
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
                                res = generate_image_by_text(client, st.session_state.current_pose_texts[i], identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur)
                                if isinstance(res, Image.Image):
                                    st.session_state.generated_images[i] = res; st.rerun()
                                else: st.error(f"再生成失敗: {res}")
