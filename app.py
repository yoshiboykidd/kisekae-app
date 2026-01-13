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

# --- 1. システム設定・定数初期化 ---
VERSION = "2.5"
# セッション状態の初期化
if "generated_images" not in st.session_state:
    st.session_state.generated_images = [None] * 4
if "error_log" not in st.session_state:
    st.session_state.error_log = []
if "anchor_part" not in st.session_state:
    st.session_state.anchor_part = None
if "wardrobe_task" not in st.session_state:
    st.session_state.wardrobe_task = ""

# ポーズリスト（ここがないとエラーになるため再定義）
STAND_PROMPTS = [
    "Full body portrait, standing naturally, hand touching hair",
    "Full body portrait, leaning slightly against a wall",
    "Full body portrait, looking back over shoulder",
    "Full body portrait, one hand on hip, relaxed"
]
SIT_PROMPTS = [
    "Full body portrait, sitting on a sofa, looking at camera",
    "Full body portrait, sitting gracefully on steps"
]

CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual everyday Japanese fashion", "env": "Natural daylight", "back_prompt": "natural skin texture"},
    "2. 水着（ビーチ）": {"en": "High-end stylish beachwear", "env": "Sunny resort", "back_prompt": "healthy skin glow"},
    "3. 部屋着（リラックス）": {"en": "Soft lounge wear", "env": "Warm dim lighting", "back_prompt": "ultra-soft focus, silk texture"},
    "4. オフィス（スーツ）": {"en": "Elegant business professional", "env": "Modern office", "back_prompt": "sharp corporate lighting"},
    "5. コスチューム": {"en": "High-quality themed costume", "env": "Studio setup", "back_prompt": "meticulous costume details"},
    "6. 夜の装い（ドレス）": {"en": "Sophisticated evening gown", "env": "Luxury lounge", "back_prompt": "dramatic evening lighting"}
}

# --- 2. 生成関数 (エラーキャッチ強化) ---
def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, enable_blur, cat_info):
    full_prompt = (
        f"[IDENTITY_FIX: STRICT PHYSICAL FIDELITY TO VERSION 2.5. IMAGE 1 IS THE ONLY SOURCE FOR FACE AND BODY.]\n"
        f"1. CLOTHING & TEXTURE: {cat_info['en']}. {cat_info['back_prompt']}. {wardrobe_task}\n"
        f"2. POSE: {pose_text}.\n"
        f"3. SCENE: {bg_prompt}. 85mm portrait.\n"
        f"Maintain 100% anatomical match to IMAGE 1."
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
            return Image.open(io.BytesIO(img_data)).resize((600, 900))
        else:
            return "SAFETY_ERROR" # 規制によるブロック
    except Exception as e:
        return f"API_ERROR: {str(e)}"

# --- 3. UI 構築 ---
st.title(f"📸 AI KISEKAE Manager ver {VERSION}")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# (サイドバー等の入力部は以前のコードと同様のため中略)
with st.sidebar:
    source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
    ref_img = st.file_uploader("衣装参考 (IMAGE 2 / 任意)", type=['png', 'jpg', 'jpeg'])
    cloth_main = st.selectbox("衣装カテゴリ", list(CATEGORIES.keys()))
    cloth_detail = st.text_input("衣装仕様書")
    bg_text = st.text_input("場所", "高級ホテル")
    time_of_day = st.radio("時間帯", ["昼", "夕方", "夜"])
    pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
    run_btn = st.button("✨ 4枚一括生成")

# --- 4. 生成実行メイン ---
if run_btn and source_img:
    # 状態リセット
    st.session_state.generated_images = [None] * 4
    st.session_state.error_log = []
    
    # ポーズ抽選
    if pose_pattern == "立ち3:座り1":
        poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
    else:
        poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
    random.shuffle(poses)

    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')
    cat_data = CATEGORIES[cloth_main]
    
    # ステップ1: アンカー（設計図）生成
    with st.spinner("衣装の設計図（アンカー）を生成中..."):
        # (アンカー生成ロジック実行... 失敗時はst.session_state.error_logに記録してstop)
        # ここでは便宜上、正常終了したと仮定
        st.session_state.wardrobe_task = f"Dress her in the exact {cloth_main} style."
        # ※実際のコードではここで anchor_part を生成して保存

    # ステップ2: 4枚生成
    progress_bar = st.progress(0)
    for i, p_txt in enumerate(poses):
        res = generate_image_by_text(client, p_txt, identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, bg_text, False, cat_data)
        
        if isinstance(res, Image.Image):
            st.session_state.generated_images[i] = res
        else:
            # エラー内容をログに保存（再描画後も見えるようにする）
            error_msg = "規制ブロック" if res == "SAFETY_ERROR" else "通信エラー"
            st.session_state.error_log.append(f"{i+1}枚目: {error_msg}")
        
        progress_bar.progress((i + 1) / 4)
    
    st.rerun()

# --- 5. 結果表示エリア (ここが重要) ---
# エラーログがあれば表示
if st.session_state.error_log:
    for err in st.session_state.error_log:
        st.warning(err)

# 1枚でもあれば表示
if any(st.session_state.generated_images):
    st.subheader("🖼️ 生成結果")
    cols = st.columns(2)
    for i, img in enumerate(st.session_state.generated_images):
        if img:
            with cols[i % 2]:
                st.image(img, use_container_width=True)
else:
    if run_btn: # ボタンを押したのに1枚もない場合
        st.error("生成に失敗したか、すべての画像が規制されました。衣装仕様書の表現をマイルドにしてみてください。")
