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

# --- 1. システム設定・定数初期化 (ver 2.5) ---
VERSION = "2.5"
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

# 【裏プロンプト統合版】6つのカテゴリー定義
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

# --- 2. ユーティリティ & 生成エンジン ---
def apply_face_blur(img, radius=30):
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').detectMultiScale(cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY), 1.05, 3)
    if len(faces) == 0: return img
    mask = Image.new('L', img.size, 0); draw = ImageDraw.Draw(mask)
    for (x, y, w, h) in faces: 
        draw.ellipse([x-w*0.1, y-h*0.2, x+w*1.1, y+h*1.1], fill=255)
    return Image.composite(img.filter(ImageFilter.GaussianBlur(radius)), img, mask.filter(ImageFilter.GaussianBlur(radius/2)))

def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, enable_blur, cat_info):
    """【ver 2.5】裏プロンプトの合成とエラーハンドリング"""
    # 裏プロンプトを統合
    full_prompt = (
        f"[IDENTITY_FIX: STRICT PHYSICAL FIDELITY TO VERSION 2.5/2.43. Replicate EXACT facial structure and body mass from IMAGE 1.]\n"
        f"1. CLOTHING & TEXTURE: {cat_info['en']}. {cat_info['back_prompt']}. {wardrobe_task}\n"
        f"2. POSE: {pose_text}.\n"
        f"3. SCENE & LIGHTING: {bg_prompt}. Professional 85mm portrait, lips sealed.\n"
        f"Maintain 100% anatomical match to the woman in IMAGE 1."
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
    except Exception as e:
        st.error(f"APIエラーが発生しました: {str(e)}")
    return None

# --- 3. UI 構築 ---
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if not st.session_state.password_correct:
    st.title(f"🔐 Login ver {VERSION}")
    if st.text_input("合言葉", type="password") == "karin10" and st.button("ログイン"):
        st.session_state.password_correct = True; st.rerun()
    st.stop()

st.title(f"📸 AI KISEKAE Manager ver {VERSION}")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

with st.sidebar:
    cast_name = st.text_input("👤 キャスト名", "cast")
    source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
    ref_img = st.file_uploader("衣装参考 (IMAGE 2 / 任意)", type=['png', 'jpg', 'jpeg'])
    st.divider()
    cloth_main = st.selectbox("衣装カテゴリ", list(CATEGORIES.keys()))
    cloth_detail = st.text_input("衣装仕様書", placeholder="例：ネイビーのシルク素材、透け感あり")
    st.divider()
    bg_text = st.text_input("場所", "高級ホテル")
    time_of_day = st.radio("時間帯", ["昼", "夕方", "夜"])
    pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
    enable_blur = st.checkbox("🛡️ 楕円顔ブラー")
    run_btn = st.button("✨ 4枚一括生成")

# --- 4. 生成実行 ---
if run_btn and source_img:
    st.session_state.generated_images = [None] * 4
    # ポーズ抽選 (STAND_PROMPTS/SIT_PROMPTSは省略、以前の定義を使用)
    # ... (ポーズ抽選ロジック) ...
    
    time_mods = {"昼": "bright daylight", "夕方": "golden hour glow", "夜": "night lights"}
    cat_data = CATEGORIES[cloth_main]
    st.session_state.final_bg_prompt = f"{bg_text}, {cat_data['env']}, {time_mods[time_of_day]}"

    with st.spinner("衣装アンカーを構築中..."):
        # 衣装設計図の生成プロセス
        # ... (既存のanchor_part生成ロジック) ...
        # もしresが失敗したらエラーを出す
        if not hasattr(st.session_state, 'anchor_part') or st.session_state.anchor_part is None:
            st.error("衣装の設計図（アンカー）の生成に失敗しました。仕様書の内容をマイルドにしてみてください。")
            st.stop()

    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')
    
    # 4枚ループ生成
    success_count = 0
    progress_bar = st.progress(0)
    for i, p_txt in enumerate(st.session_state.current_pose_texts):
        img = generate_image_by_text(client, p_txt, identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, enable_blur, cat_data)
        if img:
            st.session_state.generated_images[i] = img
            success_count += 1
        else:
            st.warning(f"画像 {i+1} 枚目の生成に失敗しました（規制または通信エラー）。")
        progress_bar.progress((i + 1) / 4)
    
    if success_count == 0:
        st.error("すべての画像生成に失敗しました。画像や仕様書を変更して再度お試しください。")
    
    st.rerun()

# --- 5. 結果表示 (以下、保存・撮り直し機能など) ---
# ... (既存の表示・撮り直しロジック) ...
