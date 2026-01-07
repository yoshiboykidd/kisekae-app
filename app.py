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

    st.title("📸 AI KISEKAE [Simple & Strict]")

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        src_img = st.file_uploader("1. キャスト写真 (顔・絶対遵守)", type=['png', 'jpg', 'jpeg'])
        # ラベルを変更し、役割を明確化
        ref_img = st.file_uploader("2. 衣装参照写真 (あればこの服を着用)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        # 参考画像がある場合は無視されることを注記
        cloth_main = st.selectbox("3. スタイル (参考画像なしの場合のみ有効)", ["ワンピースドレス", "タイトミニドレス", "オフィスカジュアル", "ナースウェア", "メイドウェア", "サマー・リゾートウェア", "浴衣"])
        cloth_detail = st.text_input("追加指示", placeholder="例：黒サテン地、リボン (参考画像と併用可)")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "サマー・リゾート地"])
        st.divider()
        run_button = st.button("✨ シンプルに一括生成")

    if run_button and src_img:
        st.subheader("🖼️ 生成結果")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        base_parts = [types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # --- ロジックの単純化 ---
        # 参考画像がある場合、スタイル選択(cloth_main)は完全に無視し、
        # 「画像2の服を着ろ」とだけ指示する。
        if ref_img:
            outfit_instruction = f"WEAR THE EXACT OUTFIT shown in IMAGE 2. Ignore any other style setting. {cloth_detail}."
        else:
            outfit_instruction = f"WEAR A {cloth_main}. {cloth_detail}."

        # プロンプトを極限までシンプルかつ強力にする
        # 絶対条件を冒頭に配置
        prompt = (
            f"ABSOLUTE RULES (MUST FOLLOW):\n"
            f"1. IDENTITY: The person MUST be the woman from IMAGE 1. Keep her face and bone structure 100% IDENTICAL. Do not use the face from IMAGE 2.\n"
            f"2. MOUTH: Lips MUST be sealed. NO TEETH visible.\n\n"
            f"TASK:\n"
            f"Create a 2x2 grid photo of this woman.\n"
            f"OUTFIT: {outfit_instruction}\n"
            f"BACKGROUND: {bg}.\n"
            f"POSES: 4 different professional poses (Standing, Walking, Sitting, Close-up).\n"
            f"QUALITY: 8k photorealistic studio portrait."
        )

        with st.spinner("絶対条件を遵守して生成中..."):
            try:
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=base_parts + [prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        # 安全設定は緩いまま維持（フィルター対策）
                        safety_settings=[
                            types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                        ],
                        # 全体を2:3の比率で生成
                        image_config=types.ImageConfig(aspect_ratio="
