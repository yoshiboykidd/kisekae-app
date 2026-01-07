import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 認証機能 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 Karinto Group Image Tool")
        pwd = st.text_input("合言葉を入力してください", type="password")
        if st.button("ログイン"):
            # 合言葉は karin10
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

    st.title("📸 AI KISEKAE Manager [Reference Image Mode]")

    # --- 大胆なポーズ・ライブラリ ---
    POSE_LIBRARY = {
        "Standard (王道)": [
            "Full body shot, walking confidently toward the camera, dress fluttering.",
            "High angle full body shot, looking up at the camera with a bright expression.",
            "Full body shot, sitting on a high stool, one leg stretched forward elegantly.",
            "Full body shot, leaning against a luxury car or marble pillar.",
            "Full body shot, captured from the side, looking back with a soft smile.",
            "Full body shot, standing with a slight twist in the waist to emphasize curves.",
            "Full body shot, sitting on stairs, legs positioned at different levels.",
            "Full body shot, reaching out a hand toward the camera naturally."
        ],
        "Cool & Sexy (大胆・綺麗め)": [
            "Dramatic low angle full body shot, looking down at the camera with a sharp gaze.",
            "Full body shot, sitting on the floor with legs crossed, leaning back on hands.",
            "Full body shot, back view, looking over the shoulder with a bold expression.",
            "Full body shot, lying on a luxury sofa, showcasing a long body line.",
            "Full body shot, leaning against a wall with one knee bent and foot up.",
            "Full body shot, powerful model walk, captured in mid-stride.",
            "Full body shot, squatting elegantly in a high-fashion pose.",
            "Full body shot, arched back, arms raised slightly to highlight the silhouette."
        ],
        "Cute & Active (動きのある可愛さ)": [
            "Full body shot, jumping slightly or skipping with a joyful expression.",
            "Full body shot, twirling around, skirt expanding in a circle.",
            "Full body shot, kneeling on a soft carpet, holding a plush pillow.",
            "Full body shot, crouching down and peeking into the camera lens.",
            "Full body shot, running gently on a beach, hair wind-blown and messy-cute.",
            "Full body shot, sitting on a swing or garden bench, legs swinging.",
            "Full body shot, hugging herself gently, tilted head and winking.",
            "Full body shot, hands in hair, leaning back with a playful laugh."
        ]
    }

    with st.sidebar:
        st.subheader("
