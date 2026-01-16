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

# --- 1. システム設定 (ver 2.71: Hairstyle List Update) ---
VERSION = "2.71"
st.set_page_config(page_title=f"AI KISEKAE Manager v{VERSION}", layout="wide")

# セッション状態の初期化
for key in ["generated_images", "error_log", "anchor_part", "wardrobe_task", "current_pose_texts", "final_bg_prompt"]:
    if key not in st.session_state:
        if key == "generated_images": st.session_state[key] = [None] * 4
        elif key == "error_log": st.session_state[key] = []
        elif key in ["anchor_part", "wardrobe_task", "final_bg_prompt"]: st.session_state[key] = None
        else: st.session_state[key] = []

# --- 髪型定義マップ (指定順序に変更・追加) ---
HAIR_STYLES = {
    "元画像のまま": "original hairstyle from IMAGE 1",
    "ゆるふあ巻き": "soft loose wavy curls",
    "ハーフアップ": "elegant half-up style",
    "ツインテール": "playful twin tails",
    "ポニーテール": "neat ponytail",
    "まとめ髪": "sophisticated updo bun",
    "ストレート": "sleek long straight hair"
}

# --- 髪色定義マップ (変更なし) ---
HAIR_COLORS = {
    "元画像のまま": "original hair color from IMAGE 1",
    "ナチュラルブラック": "natural black hair",
    "ダークブラウン": "deep dark brown hair",
    "アッシュベージュ": "trendy ash beige hair color",
    "ミルクティーグレージュ": "soft milk-tea greige hair color",
    "ピンクブラウン": "subtle pinkish brown hair",
    "ハニーブロンド": "bright honey blonde hair"
}

# ポーズプール (ver 2.66 準拠)
STAND_PROMPTS = [
    "Full body portrait, standing naturally, hand gently touching hair, looking away",
    "Full body portrait, leaning against a wall, arms casually crossed",
    "Full body portrait, walking slowly, looking back over shoulder",
    "Full body portrait, standing with weight on one leg, one hand on hip"
]
SIT_PROMPTS = [
    "Full body portrait, relaxed sitting pose on a sofa, looking at camera",
    "Full body portrait, sitting sideways on a chair, leaning on the backrest",
    "Full body portrait, sitting gracefully on steps, hands resting in lap"
]

# カテゴリー定義 (ver 2.66 準拠)
CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual everyday Japanese fashion", "back_prompt": "natural soft skin, soft daylight"},
    "2. 水着（リゾート）": {"en": "High-end stylish resort swimwear", "back_prompt": "healthy skin glow, vibrant summer lighting"},
    "3. 部屋着（リラックス）": {"en": "Elegant silk night-fashion, satin camisole-style", "back_prompt": "ultra-soft focus, warm rim lighting, soft beauty face light"},
    "4. オフィス（スーツ）": {"en": "Elegant business professional attire", "back_prompt": "sharp corporate lighting, professional studio look"},
    "5. コスチューム": {"en": "High-quality themed costume, professional uniform", "back_prompt": "meticulous details, professional strobe"},
    "6. 夜の装い（ドレス）": {"en": "Sophisticated evening gown", "back_prompt": "luxury bokeh, dramatic lighting, soft facial fill-light"}
}

# --- 2. ユーティリティ ---
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

def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, hair_style_en, hair_color_en, cat_key):
    """【絶対ルール：ver 2.70 継承】顔固定を最上位に置き、髪型・髪色を反映"""
    cat_info = CATEGORIES[cat_key]
    prompt = (
        f"CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK.\n"
        f"1. FACE FIDELITY (IMAGE 1): Replicate the EXACT facial structure of IMAGE 1. 100% identity match. Maintain the original skin tone regardless of hair color.\n"
        f"2. HAIR CUSTOMIZATION: Style: {hair_style_en}, Color: {hair_color_en}. Integrate naturally without altering facial features.\n"
        f"3. PHYSICAL IDENTITY (IMAGE 1): [FIXED_IDENTITY] Match the exact body mass and curves of IMAGE 1.\n"
        f"4. POSE & COMPOSITION: {pose_text}. 85mm portrait lens.\n"
        f"5. WARDROBE (IMAGE 2): {wardrobe_task}\n"
        f"6. RENDER: {bg_prompt}, {cat_info['back_prompt']}, soft facial fill-light, 8k, lips sealed, neutral expression."
    )
    res_data = generate_with_retry(client, [identity_part, anchor_part], prompt)
    if isinstance(res_data, bytes):
        return Image.open(io.BytesIO(res_data)).resize((600, 900))
    return res_data

# --- 3. UI 構築 ---
st.title(f"📸 AI KISEKAE Manager ver {VERSION}")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

with st.sidebar:
    st.header("🛠 Control Panel")
    source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
    if source_img: st.image(source_img, use_container_width=True)
    ref_img = st.file_uploader("衣装参考 (IMAGE 2)", type=['png', 'jpg', 'jpeg'])
    if ref_img: st.image(ref_img, use_container_width=True)
    st.divider()
    cloth_main = st.selectbox("衣装カテゴリー", list(CATEGORIES.keys()))
    cloth_detail = st.text_input("衣装仕様書", placeholder="例：シルク、サテン")
    
    # 髪型アレンジ (指定順序で表示)
    hair_style_choice = st.selectbox("💇 髪型アレンジ", list(HAIR_STYLES.keys()))
    hair_color_choice = st.selectbox("🎨 髪色変更", list(HAIR_COLORS.keys()))
    
    st.divider()
    bg_text = st.text_input("場所", "高級ホテルの部屋")
    time_of_day = st.radio("時間帯", ["昼 (Daylight)", "夕方 (Golden Hour)", "夜 (Night)"])
    run_btn = st.button("✨ 4枚一括生成")

# 共通 identity_part
identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg') if source_img else None

# --- 4. 生成実行 ---
if run_btn and source_img:
    st.session_state.error_log = []
    st.session_state.generated_images = [None] * 4
    time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "warm sunset glow", "夜 (Night)": "night lights"}
    st.session_state.final_bg_prompt = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh"
    st.session_state.current_pose_texts = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
    random.shuffle(st.session_state.current_pose_texts)

    status_container = st.empty()
    progress_bar = st.progress(0)

    # Step 1: アンカー
    with status_container.container():
        st.info("🕒 Step 1/2: 衣装設計図を構築中...")
        anchor_prompt = f"Studio product shot of {CATEGORIES[cloth_main]['en']}. Specs: {cloth_detail}. Isolated view."
        contents = [types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')] if ref_img else []
        res_data = generate_with_retry(client, contents, anchor_prompt)
        if isinstance(res_data, bytes):
            st.session_state.anchor_part = types.Part.from_bytes(data=res_data, mime_type='image/png')
            st.session_state.wardrobe_task = f"Strictly replicate the fashion design from IMAGE 2. {cloth_detail}."
        else:
            st.error(f"アンカー失敗: {res_data}"); st.stop()

    # Step 2: 4枚生成
    for i, p_txt in enumerate(st.session_state.current_pose_texts):
        with status_container.container(): st.info(f"🎨 Step 2/2: 顔面固定 + ヘアメイク中 ({i+1}/4)...")
        img_res = generate_image_by_text(
            client, p_txt, identity_part, st.session_state.anchor_part, 
            st.session_state.wardrobe_task, st.session_state.final_bg_prompt, 
            HAIR_STYLES[hair_style_choice], HAIR_COLORS[hair_color_choice], cloth_main
        )
        if isinstance(img_res, Image.Image): st.session_state.generated_images[i] = img_res
        else: st.session_state.error_log.append(f"{i+1}枚目: {img_res}")
        progress_bar.progress((i+1)/4); time.sleep(1)

    status_container.success("✨ 生成完了！"); time.sleep(0.5); status_container.empty(); st.rerun()

# --- 5. 表示エリア ---
if any(st.session_state.generated_images):
    cols = st.columns(2)
    for i in range(4):
        with cols[i % 2]:
            img = st.session_state.generated_images[i]
            if img:
                st.image(img, use_container_width=True)
                # 個別撮り直しボタン
                if st.button(f"🔄 撮り直し #{i+1}", key=f"re_{i}"):
                    with st.spinner("再生成中..."):
                        res = generate_image_by_text(
                            client, st.session_state.current_pose_texts[i], identity_part, 
                            st.session_state.anchor_part, st.session_state.wardrobe_task, 
                            st.session_state.final_bg_prompt, HAIR_STYLES[hair_style_choice], 
                            HAIR_COLORS[hair_color_choice], cloth_main
                        )
                        if isinstance(res, Image.Image): st.session_state.generated_images[i] = res; st.rerun()
            else:
                st.info(f"🔳 スロット {i+1}: 生成失敗")
                if st.button(f"⚡ 再送 #{i+1}", key=f"retry_{i}", type="primary"):
                    with st.spinner("再送中..."):
                        res = generate_image_by_text(
                            client, st.session_state.current_pose_texts[i], identity_part, 
                            st.session_state.anchor_part, st.session_state.wardrobe_task, 
                            st.session_state.final_bg_prompt, HAIR_STYLES[hair_style_choice], 
                            HAIR_COLORS[hair_color_choice], cloth_main
                        )
                        if isinstance(res, Image.Image): st.session_state.generated_images[i] = res; st.rerun()
