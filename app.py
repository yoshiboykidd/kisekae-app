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

# --- 1. システム設定・定数初期化 (ver 2.52) ---
# ルール：修正のたびにバージョンを更新。黄金律 2.43 を継承。
VERSION = "2.52"
st.set_page_config(page_title=f"AI KISEKAE Manager v{VERSION}", layout="wide")

# セッション状態の初期化
for key in ["generated_images", "error_log", "anchor_part", "wardrobe_task", "current_pose_texts"]:
    if key not in st.session_state:
        if key == "generated_images": st.session_state[key] = [None] * 4
        elif key == "error_log": st.session_state[key] = []
        elif key in ["anchor_part", "wardrobe_task"]: st.session_state[key] = None
        else: st.session_state[key] = []

# ポーズ定義（2.43 黄金律）
STAND_PROMPTS = [
    "Full body portrait, standing naturally with a relaxed posture, hand gently touching hair, looking slightly away from camera, candid style",
    "Full body portrait, leaning slightly against a wall, arms casually crossed, natural smile, angled body position",
    "Full body portrait, captured mid-movement like slowly walking, looking back over shoulder",
    "Full body portrait, standing with weight on one leg, one hand resting on hip, confident and relaxed look",
    "Full body portrait, standing by a railing, looking out with a thoughtful expression"
]
SIT_PROMPTS = [
    "Full body portrait, relaxed sitting pose on a sofa, one leg tucked naturally, looking at camera",
    "Full body portrait, sitting sideways on a chair, leaning slightly on the backrest, relaxed posture",
    "Full body portrait, sitting gracefully on steps, hands resting naturally in lap",
    "Full body portrait, casual sitting pose on a plush surface, leaning back slightly on hands"
]

# 6つの固定カテゴリー定義
CATEGORIES = {
    "1. 私服（日常）": "Casual everyday Japanese fashion",
    "2. 水着（ビーチ）": "High-end stylish beachwear",
    "3. 部屋着（リラックス）": "Soft lounge wear, silk or knit lingerie-style",
    "4. オフィス（スーツ）": "Elegant business professional attire",
    "5. コスチューム": "High-quality themed costume, professional uniform",
    "6. 夜の装い（ドレス）": "Sophisticated evening gown, glamorous cocktail fashion"
}

# --- 2. ユーティリティ関数 ---
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

def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, enable_blur):
    """【絶対ルール遵守】2.43 アイデンティティ固定プロンプト"""
    prompt = (
        f"STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK.\n"
        f"1. PHYSICAL IDENTITY (IMAGE 1): [FIXED_IDENTITY] Replicate the EXACT body mass, curves, weight, and shoulder width of the woman in IMAGE 1. Do not make her thinner. 100% anatomical match.\n"
        f"2. POSE & COMPOSITION: {pose_text}. The composition must be a natural, candid-style portrait.\n"
        f"3. FACE (IMAGE 1): Precise facial identity match. Identical features from IMAGE 1.\n"
        f"4. WARDROBE (IMAGE 2): {wardrobe_task}\n"
        f"5. SCENE: {bg_prompt}, 85mm portrait, professional lighting, Japanese woman, masterpiece quality, lips sealed."
    )
    
    try:
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
        else:
            return "SAFETY_BLOCK" # 規制によるエラー
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- 3. 認証・UI ---
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if not st.session_state.password_correct:
    st.title(f"🔐 Login ver {VERSION}")
    if st.text_input("合言葉", type="password") == "karin10" and st.button("ログイン"):
        st.session_state.password_correct = True; st.rerun()
    st.stop()

st.title(f"📸 AI KISEKAE Manager ver {VERSION}")
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

with st.sidebar:
    st.header("🛠 Settings")
    cast_name = st.text_input("👤 キャスト名", "cast")
    source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
    ref_img = st.file_uploader("衣装参考 (IMAGE 2 / 任意)", type=['png', 'jpg', 'jpeg'])
    st.divider()
    cloth_main = st.selectbox("衣装カテゴリ", list(CATEGORIES.keys()))
    cloth_detail = st.text_input("衣装仕様書", placeholder="例：黒サテン、フリル付き")
    st.divider()
    bg_text = st.text_input("場所", "高級ホテルの部屋")
    time_of_day = st.radio("時間帯", ["昼 (Daylight)", "夕方 (Golden Hour)", "夜 (Night)"], index=0)
    pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
    enable_blur = st.checkbox("🛡️ 楕円顔ブラー")
    run_btn = st.button("✨ 4枚一括生成")

# --- 4. 生成実行ロジック (エラーハンドリング強化版) ---
if run_btn and source_img:
    st.session_state.generated_images = [None] * 4
    st.session_state.error_log = []
    
    # ポーズ決定
    if pose_pattern == "立ち3:座り1":
        poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
    else:
        poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
    random.shuffle(poses)
    st.session_state.current_pose_texts = poses

    time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "warm sunset glow", "夜 (Night)": "night lights"}
    final_bg = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh background"

    # 【絶対ルール】ステップ1：アンカー生成
    with st.spinner("衣装の設計図（アンカー）を構築中..."):
        cat_en = CATEGORIES[cloth_main]
        try:
            if ref_img:
                ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
                anchor_prompt = f"Studio catalog photo of the EXACT SAME {cat_en}. Specs: {cloth_detail}. Isolated view."
                res = client.models.generate_content(model='gemini-3-pro-image-preview', contents=[ref_part, anchor_prompt], config=types.GenerateContentConfig(response_modalities=['IMAGE']))
            else:
                anchor_prompt = f"Professional catalog photo of {cat_en}. {cloth_detail}."
                res = client.models.generate_content(model='gemini-3-pro-image-preview', contents=[anchor_prompt], config=types.GenerateContentConfig(response_modalities=['IMAGE']))
            
            if res.candidates and res.candidates[0].content.parts:
                st.session_state.anchor_part = types.Part.from_bytes(data=res.candidates[0].content.parts[0].inline_data.data, mime_type='image/png')
                st.session_state.wardrobe_task = f"Strictly replicate the clothing from IMAGE 2. {cloth_detail}."
            else:
                st.error("衣装アンカーの生成が規制されました。仕様書の表現を和らげてください。")
                st.stop()
        except Exception as e:
            st.error(f"アンカー生成中にエラーが発生しました: {str(e)}")
            st.stop()

    # 【絶対ルール】ステップ2：4枚一括生成
    progress_bar = st.progress(0)
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')

    for i, p_txt in enumerate(poses):
        img_res = generate_image_by_text(client, p_txt, identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, final_bg, enable_blur)
        
        if isinstance(img_res, Image.Image):
            st.session_state.generated_images[i] = img_res
        else:
            # エラー内容をログに記録
            err_type = "規制ブロック" if img_res == "SAFETY_BLOCK" else f"通信エラー: {img_res}"
            st.session_state.error_log.append(f"{i+1}枚目: {err_type}")
        
        progress_bar.progress((i + 1) / 4)
    
    st.rerun()

# --- 5. 表示エリア ---
# エラーログの表示
if st.session_state.error_log:
    for err in st.session_state.error_log:
        st.warning(err)

if any(st.session_state.generated_images):
    st.subheader(f"🖼️ 生成結果 (ver {VERSION})")
    cols = st.columns(2)
    identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg') if source_img else None

    for i, img in enumerate(st.session_state.generated_images):
        if img:
            with cols[i % 2]:
                st.image(img, use_container_width=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"img_{i}.jpg", "image/jpeg", key=f"dl_{i}")
                with c2:
                    if st.button("🔄 撮り直し", key=f"redo_{i}"):
                        if identity_part and st.session_state.anchor_part:
                            with st.spinner("再生成中..."):
                                new_img = generate_image_by_text(client, st.session_state.current_pose_texts[i], identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, final_bg, enable_blur)
                                if isinstance(new_img, Image.Image):
                                    st.session_state.generated_images[i] = new_img
                                    st.rerun()
                                else:
                                    st.error("再生成も規制またはエラーで失敗しました。")
