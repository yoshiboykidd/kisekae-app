import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 認証機能 (karin10) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 Karinto Group Image Tool")
        pwd = st.text_input("合言葉を入力してください", type="password")
        if st.button("ログイン"):
            if pwd == "karin10": 
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("合言葉が正しくありません")
        return False
    return True

# --- 2. メインアプリ ---
if check_password():
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)

    st.title("📸 AI KISEKAE [Identity & Physique Lock]")

    # 4つの構図の定義
    POSE_SLOTS = {
        "A: 正面（全身）": "A formal full-body fashion shot, standing straight, facing forward.",
        "B: 動き（全身）": "A dynamic full-body shot, walking or turning pose.",
        "C: 座り（全身）": "A full-body shot sitting elegantly on a chair or floor.",
        "D: 寄り（バストアップ）": "A beauty portrait shot from the chest up, focusing on the face."
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. キャスト写真 (顔・体型：絶対遵守)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装参照画像 (布地の柄・色のみ引用)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル設定", ["ワンピースドレス", "タイトミニドレス", "オフィスカジュアル", "ナーススタイル", "メイドスタイル", "スイムウェア", "浴衣"])
        cloth_detail = st.text_input("衣装の追加指示", placeholder="例：黒のサテン地、フリル付き")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の街並み", "撮影スタジオ", "カフェテラス", "プライベートビーチ"])
        st.divider()
        run_button = st.button("✨ 4枚一括生成開始")

    if run_button and
