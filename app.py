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

# --- 1. 固定背景リスト ---
BG_OPTIONS = {
    "高級スイートルーム (温かい照明)": "Luxury hotel presidential suite with warm soft lighting",
    "大理石のホテルロビー (豪華なシャンデリア)": "Grand marble lobby of a 5-star hotel with elegant chandeliers",
    "落ち着いたホテルラウンジ (夜)": "Sophisticated dim-lit hotel lounge with leather sofas",
    "高級ワインセラー (黄金色の光)": "Modern high-end wine cellar with golden ambient lighting",
    "都会の夜景 (キラキラしたボケ)": "Shimmering city night view of Tokyo with colorful bokeh lights",
    "夜の銀座ネオン街 (柔らかなフレア)": "Brightly lit neon street in Ginza at night with soft lens flares",
    "オープンカフェテラス (暖色の街灯)": "Chic open-air cafe terrace with warm fairy lights",
    "水辺のテラス (ライトアップされた橋)": "Modern waterfront balcony overlooking a lit-up bridge",
    "陽光が差し込む明るいテラス (自然光)": "Sunny outdoor terrace with soft natural sunlight and greenery bokeh",
    "白を基調とした明るいリビング": "Bright minimalist luxury living room with white interior and soft morning light",
    "緑の見える午後の公園 (透明感)": "Beautiful park with lush green trees and soft afternoon sun, deep bokeh",
    "白い建物が並ぶ静かな街路 (爽やか)": "Quiet street with elegant white buildings and clear blue sky",
    "夜のインフィニティプール": "Luxury infinity pool at night with turquoise water reflections",
    "夜桜の庭園": "Elegant Japanese garden with cherry blossoms at night (Yozakura)",
    "伝統的な和室 (行灯の光)": "Traditional Japanese room with tatami and soft paper lantern light",
    "紅葉の夕暮れ庭園": "Serene autumn garden with red maple leaves and soft evening sun"
}

# --- 2. ポーズ選出ロジック ---
def get_4_preset_poses(pattern="立ち3:座り1"):
    base_path = "presets/poses"
    stand_dir = os.path.join(base_path, "standing")
    sit_dir = os.path.join(base_path, "sitting")

    def get_set_ids(directory):
        if not os.path.exists(directory): return []
        files = os.listdir(directory)
        ids = []
        for f in files:
            parts = f.split('_')
            if len(parts) >= 2:
                ids.append(f"{parts[0]}_{parts[1]}")
        return sorted(list(set(ids)))

    def find_file(directory, set_id, angle_keywords):
        if not os.path.exists(directory): return None
        files = os.listdir(directory)
        for f in files:
            if f.startswith(set_id):
                for kw in angle_keywords:
                    if kw.lower() in f.lower():
                        return os.path.join(directory, f)
        return None

    stand_sets = get_set_ids(stand_dir)
    sit_sets = get_set_ids(sit_dir)

    if pattern == "立ち3:座り1" and (len(stand_sets) < 3 or len(sit_sets) < 1):
        st.error(f"セット不足: 立ち{len(stand_sets)}, 座り{len(sit_sets)}")
        return []
    
    selected_paths = []
    try:
        if pattern == "立ち3:座り1":
            chosen_s = random.sample(stand_sets, 3)
            chosen_t = random.sample(sit_sets, 1)
            selected_paths.append(find_file(stand_dir, chosen_s[0], ["Front", "Frot"]))
            selected_paths.append(find_file(stand_dir, chosen_s[1], ["Quarter"]))
            selected_paths.append(find_file(stand_dir, chosen_s[2], ["Low"]))
            selected_paths.append(find_file(sit_dir, chosen_t[0], ["High"]))
        else:
            chosen_s = random.sample(stand_sets, 2)
            chosen_t = random.sample(sit_sets, 2)
            selected_paths.append(find_file(stand_dir, chosen_s[0], ["Front", "Frot"]))
            selected_paths.append(find_file(stand_dir, chosen_s[1], ["Low"]))
            selected_paths.append(find_file(sit_dir, chosen_t[0], ["Quarter"]))
            selected_paths.append(find_file(sit_dir, chosen_t[1], ["High"]))
    except Exception as e:
        st.error(f"ポーズ選出エラー: {e}")
        return []

    return [p for p in selected_paths if p is not None]

# --- 3. 顔ブラー処理 ---
def apply_face_blur(pil_image, blur_radius):
    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30))
    if len(faces) == 0:
        side_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
        faces = side_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3)
    if len(faces) == 0: return pil_image
    blurred_image = pil_image.filter(ImageFilter.GaussianBlur(blur_radius))
    mask = Image.new('L', pil_image.size, 0)
    draw = ImageDraw.Draw(mask)
    for (x, y, w, h) in faces:
        margin_w = int(w * 0.15); margin_h = int(h * 0.2)
        ellipse_box = [x - margin_w, y - margin_h * 1.3, x + w + margin_w, y + h + margin_h]
        draw.ellipse(ellipse_box, fill=255, outline=255)
    mask_blurred = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius/2))
    return Image.composite(blurred_image, pil_image, mask_blurred)

# --- 4. 認証機能 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 Karinto Group Image Tool ver 2.17")
        pwd = st.text_input("合言葉", type="password")
        if st.button("ログイン"):
            if pwd == "karin10": 
                st.session_state["password_correct"] = True; st.rerun()
            else: st.error("不一致")
        return False
    return True

# --- 5. メインアプリ ---
if check_password():
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
    st.title("📸 AI KISEKAE Manager ver 2.17")

    with st.sidebar:
        st.subheader("👤 写真アップロード")
        source_img = st.file_uploader("キャスト写真", type=['png', 'jpg', 'jpeg'])
        if source_img: st.image(source_img, use_container_width=True)
        ref_img = st.file_uploader("衣装参考 (任意)", type=['png', 'jpg', 'jpeg'])
        if ref_img: st.image(ref_img, use_container_width=True)
            
        st.divider()
        cloth_main = st.selectbox("ベース衣装カテゴリー", ["タイトミニドレス", "清楚ワンピース", "水着", "浴衣", "ナース服", "その他"])
        cloth_detail = st.text_input("衣装補足指示", placeholder="例：黒サテン、フリル付き")
        
        st.divider()
        st.subheader("🌄 背景設定")
        selected_bg_label = st.selectbox("背景リストから選択", list(BG_OPTIONS.keys()))
        bg_free_text = st.text_input("背景の自由入力 (こちら優先)", placeholder="例: ひまわり畑")
        
        st.divider()
        pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
        enable_blur = st.checkbox("🛡️ 楕円顔ブラーを自動適用", value=False)
        blur_strength = st.select_slider("ブラー強度", options=["弱", "中", "強"], value="中") if enable
