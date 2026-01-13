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

# --- 1. システム設定・定数初期化 (ver 2.51) ---
VERSION = "2.51"
st.set_page_config(page_title=f"AI KISEKAE Manager v{VERSION}", layout="wide")

# セッション状態の初期化
if "generated_images" not in st.session_state:
    st.session_state.generated_images = [None] * 4
if "error_log" not in st.session_state:
    st.session_state.error_log = []
if "anchor_part" not in st.session_state:
    st.session_state.anchor_part = None
if "wardrobe_task" not in st.session_state:
    st.session_state.wardrobe_task = ""
if "current_pose_texts" not in st.session_state:
    st.session_state.current_pose_texts = []

# ポーズ定義（2.43からの黄金律）
STAND_PROMPTS = [
    "Full body portrait, standing naturally with a relaxed posture, hand gently touching hair, looking slightly away, candid style",
    "Full body portrait, leaning slightly against a wall, arms casually crossed, natural expression",
    "Full body portrait, captured mid-movement like slowly walking, looking back over shoulder",
    "Full body portrait, standing with weight on one leg, one hand on hip, confident and relaxed",
    "Full body portrait, standing by a railing, looking out with a thoughtful expression"
]
SIT_PROMPTS = [
    "Full body portrait, relaxed sitting pose on a sofa, one leg tucked naturally, looking at camera",
    "Full body portrait, sitting sideways on a chair, leaning slightly on the backrest, relaxed posture",
    "Full body portrait, sitting gracefully on steps, hands resting naturally in lap",
    "Full body portrait, casual sitting pose on a plush surface, leaning back slightly on hands"
]

# 【裏プロンプト統合】6つのカテゴリー定義
CATEGORIES = {
    "1. 私服（日常）": {
        "en": "Casual everyday Japanese fashion",
        "env": "Natural daylight, street or cafe",
        "back_prompt": "natural soft skin texture, high-quality fabric weave, morning sun, candid photography style"
    },
    "2. 水着（ビーチ）": {
        "en": "High-end stylish beachwear",
        "env": "Sunny resort, poolside",
        "back_prompt": "healthy sun-kissed skin glow, water droplets on skin, sharp contrast, vibrant summer lighting"
    },
    "3. 部屋着（リラックス）": {
        "en": "Soft lounge wear, silk or knit lingerie-style",
        "env": "Cozy bedroom, warm dim lighting",
        "back_prompt": "ultra-soft focus, warm rim lighting, delicate lace and silk texture, intimate and cinematic atmosphere"
    },
    "4. オフィス（スーツ）": {
        "en": "Elegant business professional",
        "env": "Modern office, clean lighting",
        "back_prompt": "sharp corporate lighting, professional studio look, high-contrast silhouette, sophisticated texture"
    },
    "5. コスチューム": {
        "en": "High-quality themed costume",
        "env": "Studio setup, concept background",
        "back_prompt": "meticulous costume details, professional studio strobe lighting, crisp fabric textures, theatrical mood"
    },
    "6. 夜の装い（ドレス）": {
        "en": "Sophisticated evening gown",
        "env": "Luxury lounge, night city bokeh",
        "back_prompt": "dramatic evening lighting, luxury satin sheen, glamorous bokeh background, high-end fashion photography"
    }
}

# --- 2. ユーティリティ関数 ---
def apply_face_blur(img, radius=30):
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').detectMultiScale(cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY), 1.05, 3)
    if len(faces) == 0: return img
    mask = Image.new('L', img.size, 0); draw = ImageDraw.Draw(mask)
    for (x, y, w, h) in faces: 
        draw.ellipse([x-w*0.1, y-h*0.2, x+w*1.1, y+h*1.1], fill=255)
    return Image.composite(img.filter(ImageFilter.GaussianBlur(radius)), img, mask.filter(ImageFilter.GaussianBlur(radius/2)))

def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, enable_blur, cat_info):
    """【ver 2.51】衣装一貫性の絶対服従ロジック"""
    full_prompt = (
        f"[CORE RULE: ABSOLUTE VISUAL FIDELITY]\n"
        f"1. IDENTITY (IMAGE 1): Replicate the exact face and body of the woman in IMAGE 1. STRICT FIDELITY to Version 2.43/2.5 proportions.\n"
        f"2. WARDROBE (IMAGE 2): **STRICTLY COPY** the outfit from IMAGE 2. Every detail, color, and texture must be IDENTICAL to IMAGE 2. No creative variations. Same photo shoot.\n"
        f"3. POSE: {pose_text}.\n"
        f"4. ENVIRONMENT: {bg_prompt}. {cat_info['back_prompt']}. 85mm lens portrait.\n"
        f"Ensure all 4 images maintain 100% clothing consistency."
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-3-pro-image-preview',
            contents=[identity_part, anchor_part, full_prompt],
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
        else: return "SAFETY_ERROR"
    except Exception as e: return f"API_ERROR: {str(e)}"

# --- 3. 認証・UI ---
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if not st.session_state.password_correct:
    st.title(f"🔐 Login ver {VERSION}")
    if st.text_input("合言葉", type="password") == "karin10" and st.button("ログイン"):
        st.session_state.password_correct = True; st.rerun()
    st.stop()

# メインタイトル表示
st.markdown(f"### 📸 AI KISEKAE Manager <span style='font-size:0.8em; color:gray;'>ver {VERSION}</span>", unsafe_allow_html=True)
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# サイドバー設定
with st.sidebar:
    st.header("🛠 Control Panel")
    cast_name = st.text_input("👤 キャスト名", "cast")
    source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
    if source_img: st.image(source_img, caption="キャストプレビュー", use_container_width=True)
    
    ref_img = st.file_uploader("衣装参考 (IMAGE 2 / 任意)", type=['png', 'jpg', 'jpeg'])
    if ref_img: st.image(ref_img, caption="衣装参考プレビュー", use_container_width=True)
            
    st.divider()
    cloth_main = st.selectbox("衣装カテゴリ", list(CATEGORIES.keys()))
    cloth_detail = st.text_input("衣装仕様書", placeholder="例：黒サテン、フリル付き")
    
    st.divider()
    st.subheader("🌅 背景・時間帯")
    bg_text = st.text_input("場所を自由入力", "高級ホテルの部屋")
    time_of_day = st.radio("時間帯", ["昼", "夕方", "夜"], index=0)
    
    st.divider()
    pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
    enable_blur = st.checkbox("🛡️ 楕円顔ブラー")
    run_btn = st.button("✨ 4枚一括生成")

# --- 4. 生成実行ロジック ---
if run_btn and source_img:
    st.session_state.generated_images = [None] * 4
    st.session_state.error_log = []
    
    # ポーズ抽選
    if pose_pattern == "立ち3:座り1":
        st.session_state.current_pose_texts = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
    else:
        st.session_state.current_pose_texts = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
    random.shuffle(st.session_state.current_pose_texts)

    time_mods = {"昼": "bright daylight", "夕方": "warm sunset glow", "夜": "night lights"}
    cat_data = CATEGORIES[cloth_main]
    final_bg = f"{bg_text}, {cat_data['env']}, {time_mods[time_of_day]}, portrait bokeh background"

    # 【ステップ1】衣装アンカー生成
    with st.spinner("衣装の設計図（アンカー）を構築中..."):
        cat_en = cat_data["en"]
        if ref_img:
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            anchor_prompt = f"Studio catalog photo of the EXACT SAME {cat_en}. Specs: {cloth_detail}. Clear lighting, isolated view."
            res = client.models.generate_content(model='gemini-3-pro-image-preview', contents=[ref_part, anchor_prompt], config=types.GenerateContentConfig(response_modalities=['IMAGE'], image_config=types.ImageConfig(aspect_ratio="1:1")))
        else:
            anchor_prompt = f"Professional catalog photo of {cat_en}. {cloth_detail}. High-quality fabric, neutral background."
            res = client.models.generate_content(model='gemini-3-pro-image-preview', contents=[anchor_prompt], config=types.GenerateContentConfig(response_modalities=['IMAGE'], image_config=types.ImageConfig(aspect_ratio="1:1")))
        
        if res.candidates and res.candidates[0].content.parts:
            st.session_state.anchor_part = types.Part.from_bytes(data=res.candidates[0].content.parts[0].inline_data.data, mime_type='image/png')
            st.session_state.wardrobe_task = f"Strictly replicate the clothing from IMAGE 2. No changes to design or color."
        else:
            st.error("アンカー生成に失敗しました。仕様書の言葉をマイルドにしてください。")
            st.stop()

    # 【ステップ2】4枚一括生成
    progress_bar = st.progress(0)
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')

    for i, p_txt in enumerate(st.session_state.current_pose_texts):
        img_res = generate_image_by_text(client, p_txt, identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, final_bg, enable_blur, cat_data)
        if isinstance(img_res, Image.Image):
            st.session_state.generated_images[i] = img_res
        else:
            err_msg = "規制ブロック" if img_res == "SAFETY_ERROR" else "通信エラー"
            st.session_state.error_log.append(f"{i+1}枚目: {err_msg}")
        progress_bar.progress((i + 1) / 4)
    
    progress_bar.empty()
    st.rerun()

# --- 5. 結果表示エリア ---
# エラーログ表示
if st.session_state.error_log:
    for err in st.session_state.error_log:
        st.warning(err)

# 生成画像表示
if any(st.session_state.generated_images):
    st.subheader(f"🖼️ 生成結果 (ver {VERSION})")
    cols = st.columns(2)
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg') if source_img else None
    
    for i, img in enumerate(st.session_state.generated_images):
        if img:
            with cols[i % 2]:
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
                                new_img = generate_image_by_text(client, st.session_state.current_pose_texts[i], identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, final_bg, enable_blur, CATEGORIES[cloth_main])
                                if isinstance(new_img, Image.Image):
                                    st.session_state.generated_images[i] = new_img
                                    st.rerun()
                                else:
                                    st.error("撮り直しに失敗しました。")
