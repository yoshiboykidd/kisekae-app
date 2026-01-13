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

# --- 1. セッション・定数初期化 ---
if "generated_images" not in st.session_state:
    st.session_state.generated_images = [None] * 4
if "current_pose_texts" not in st.session_state:
    st.session_state.current_pose_texts = []
if "anchor_part" not in st.session_state:
    st.session_state.anchor_part = None
if "wardrobe_task" not in st.session_state:
    st.session_state.wardrobe_task = ""
if "final_bg_prompt" not in st.session_state:
    st.session_state.final_bg_prompt = ""

# AIへのポーズ指示（自然なポートレート構図に変更）
STAND_PROMPTS = [
    "Full body portrait, standing naturally with a relaxed posture, hand gently touching hair, looking slightly away from camera, candid style",
    "Full body portrait, leaning slightly against a wall or surface, arms casually crossed, soft natural smile, angled body",
    "Full body portrait, captured mid-movement like slowly walking, looking back over shoulder with a gentle expression",
    "Full body portrait, a dynamic pose standing with weight on one leg, one hand in pocket or resting on hip, confident look",
    "Full body portrait, standing by a window or railing, looking out with a thoughtful expression, soft side lighting"
]

SIT_PROMPTS = [
    "Full body portrait, relaxed sitting pose on a sofa or chair, one leg tucked underneath or casually crossed, looking at camera with a gentle smile",
    "Full body portrait, sitting sideways on a chair, leaning slightly on the backrest, relaxed and engaging posture",
    "Full body portrait, sitting gracefully on a stool or steps, hands resting naturally in lap, looking slightly off-camera",
    "Full body portrait, a casual sitting pose on the floor or a low seat, leaning back slightly on hands, comfortable atmosphere"
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

def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, enable_blur):
    """テキスト指示ベースの画像生成 (ver 2.42: 自然な構図強化)"""
    prompt = (
        f"STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK.\n"
        f"1. PHYSICAL IDENTITY (IMAGE 1): Replicate the EXACT body mass, curves, weight, and shoulder width of the woman in IMAGE 1. Do not make her thinner. 100% anatomical match.\n"
        f"2. POSE & COMPOSITION: {pose_text}. The composition must be a natural, candid-style portrait. Avoid stiff, posed, or 'mugshot-like' frontal stances. Capture a relaxed and engaging moment.\n"
        f"3. FACE (IMAGE 1): Precise facial identity match. Identical features from IMAGE 1.\n"
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
    st.title("🔐 Login ver 2.42")
    if st.text_input("合言葉", type="password") == "karin10" and st.button("ログイン"):
        st.session_state.password_correct = True; st.rerun()
    st.stop()

st.title("📸 AI KISEKAE Manager ver 2.42")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

with st.sidebar:
    cast_name = st.text_input("👤 キャスト名", "cast")
    source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
    if source_img: st.image(source_img, caption="キャストプレビュー", use_container_width=True)
    
    ref_img = file_uploader("衣装参考 (IMAGE 2 / 任意)", type=['png', 'jpg', 'jpeg'])
    if ref_img: st.image(ref_img, caption="衣装参考プレビュー", use_container_width=True)
            
    st.divider()
    cloth_main = st.selectbox("衣装カテゴリ", ["タイトミニドレス", "清楚ワンピース", "水着", "浴衣", "ナース服", "その他"])
    cloth_detail = st.text_input("衣装仕様書", placeholder="例：黒サテン、フリル付き")
    
    st.divider()
    st.subheader("🌅 背景・時間帯")
    bg_text = st.text_input("場所を自由入力", "高級ホテルの部屋")
    time_of_day = st.radio("時間帯", ["昼 (Daylight)", "夕方 (Golden Hour)", "夜 (Night)"], index=0)
    
    st.divider()
    # 立ち・座り配分の選択
    pose_pattern = st.radio("生成配分 (自然なポーズ)", ["立ち3:座り1", "立ち2:座り2"])
    
    enable_blur = st.checkbox("🛡️ 楕円顔ブラー")
    run_btn = st.button("✨ 4枚一括生成")

# --- 4. 生成実行ロジック ---
if run_btn and source_img:
    st.session_state.generated_images = [None] * 4
    
    # 1. 配分に合わせてテキストポーズのリストを作成
    if pose_pattern == "立ち3:座り1":
        st.session_state.current_pose_texts = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
    else:
        st.session_state.current_pose_texts = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
    random.shuffle(st.session_state.current_pose_texts) # 順番をシャッフル

    time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "warm sunset glow", "夜 (Night)": "night lights"}
    st.session_state.final_bg_prompt = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh background"

    # 2. 衣装アンカー確定
    with st.spinner("衣装の設計図を構築中..."):
        if ref_img:
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            anchor_prompt = f"Studio catalog photo of the EXACT SAME outfit. Specs: {cloth_detail}. Isolated view."
            res = client.models.generate_content(model='gemini-3-pro-image-preview', contents=[ref_part, anchor_prompt], config=types.GenerateContentConfig(response_modalities=['IMAGE'], image_config=types.ImageConfig(aspect_ratio="1:1")))
        else:
            anchor_prompt = f"Professional catalog photo of {cloth_main}. {cloth_detail}."
            res = client.models.generate_content(model='gemini-3-pro-image-preview', contents=[anchor_prompt], config=types.GenerateContentConfig(response_modalities=['IMAGE'], image_config=types.ImageConfig(aspect_ratio="1:1")))
        
        if res.candidates:
            st.session_state.anchor_part = types.Part.from_bytes(data=res.candidates[0].content.parts[0].inline_data.data, mime_type='image/png')
            st.session_state.wardrobe_task = f"Replicate IMAGE 2 exactly. Specs: {cloth_detail}."
        else: st.stop()

    # 3. 生成ループ
    progress_bar = st.progress(0)
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')

    for i, p_txt in enumerate(st.session_state.current_pose_texts):
        img = generate_image_by_text(client, p_txt, identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur)
        if img:
            st.session_state.generated_images[i] = img
        progress_bar.progress((i + 1) / 4)
    progress_bar.empty()
    st.rerun()

# --- 5. 表示 ---
if any(st.session_state.generated_images):
    st.subheader(f"🖼️ 生成結果 ({pose_pattern})")
    cols = st.columns(2)
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg') if source_img else None

    for i, img in enumerate(st.session_state.generated_images):
        if img:
            with cols[i % 2]:
                # ラベル判定
                p_type = "立ち" if "standing" in st.session_state.current_pose_texts[i] else "座り"
                st.image(img, caption=f"ポーズ: {p_type}", use_container_width=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button(f"💾 保存", buf.getvalue(), f"{cast_name}_{i}.jpg", "image/jpeg", key=f"dl_{i}")
                with c2:
                    if st.button(f"🔄 撮り直し", key=f"redo_{i}"):
                        if identity_part:
                            with st.spinner(f"再生成中..."):
                                new_img = generate_image_by_text(client, st.session_state.current_pose_texts[i], identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur)
                                if new_img: st.session_state.generated_images[i] = new_img; st.rerun()
