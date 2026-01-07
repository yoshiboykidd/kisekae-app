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

    st.title("📸 AI KISEKAE [Parallel Gen Mode]")

    # 4つの構図を定義
    POSE_SLOTS = {
        "A": "Full-body standing pose, facing camera.",
        "B": "Dynamic full-body walking pose.",
        "C": "Full-body sitting pose on a chair.",
        "D": "Close-up portrait from chest up."
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. キャスト写真 (顔：絶対遵守)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装参照画像 (柄：固定用)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル設定", ["ワンピースドレス", "タイトミニドレス", "オフィスカジュアル", "ナーススタイル", "メイドスタイル", "スイムウェア", "浴衣"])
        cloth_detail = st.text_input("衣装の追加指示", placeholder="例：黒のサテン地、フリル付き")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の街並み", "撮影スタジオ", "カフェテラス", "プライベートビーチ"])
        st.divider()
        run_button = st.button("✨ 4枚一括生成開始")

    if run_button and source_img:
        st.subheader("🖼️ 生成結果")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        # AIに渡す画像パーツ
        base_parts = [types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # 衣装の統一指示（全画像共通）
        if ref_img:
            cloth_task = (
                f"OUTFIT SOURCE: Replicate the EXACT color, pattern, and material from IMAGE 2. "
                f"Apply this IDENTICAL design onto a {cloth_main} style. {cloth_detail}."
            )
        else:
            cloth_task = f"OUTFIT: A high-quality {cloth_main}. {cloth_detail}."

        # 4枚並列生成のプロンプトを構築
        # AIに「4つの異なるポーズで、同じ人物・同じ服のグリッド画像を作成せよ」と指示
        parallel_prompt = (
            f"TASK: Create a 2x2 grid image containing 4 distinct photographs of the person from IMAGE 1. "
            f"STRICT RULE 1 (IDENTITY): All 4 images MUST show the exact same person and face from IMAGE 1. IGNORE the face in IMAGE 2. "
            f"STRICT RULE 2 (OUTFIT): All 4 images MUST wear the EXACT SAME OUTFIT based on: {cloth_task} "
            f"STRICT RULE 3 (POSES): The 4 images must have these different poses: "
            f"Top-Left: {POSE_SLOTS['A']}, Top-Right: {POSE_SLOTS['B']}, "
            f"Bottom-Left: {POSE_SLOTS['C']}, Bottom-Right: {POSE_SLOTS['D']}. "
            f"BACKGROUND: {bg} with professional bokeh. "
            f"STYLE: 8k studio photography grid, consistent lighting across all 4 panels."
        )

        with st.spinner("4枚の画像を統一して生成中..."):
            try:
                # 1回のAPIコールで4枚のグリッド画像を生成させる
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=base_parts + [parallel_prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        safety_settings=[
                            types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                            types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                        ],
                        # グリッド画像になるため、アスペクト比は正方形に設定
                        image_config=types.ImageConfig(aspect_ratio="1:1")
                    )
                )

                if response.candidates and response.candidates[0].content.parts:
                    img_data = response.candidates[0].content.parts[0].inline_data.data
                    # 4枚が1つになったグリッド画像を取得
                    grid_img = Image.open(io.BytesIO(img_data))
                    
                    # グリッド画像を4分割して表示
                    w, h = grid_img.size
                    crop_coords = [
                        (0, 0, w//2, h//2),     # A
                        (w//2, 0, w, h//2),     # B
                        (0, h//2, w//2, h),     # C
                        (w//2, h//2, w, h)      # D
                    ]
                    
                    for i, (slot_name, _) in enumerate(POSE_SLOTS.items()):
                        with placeholders[i]:
                            # 画像をクロップ（切り出し）
                            cropped_img = grid_img.crop(crop_coords[i]).resize((600, 900))
                            st.image(cropped_img, caption=f"Pose {slot_name}", use_container_width=True)
                            
                            buf = io.BytesIO()
                            cropped_img.save(buf, format="JPEG")
                            st.download_button(
