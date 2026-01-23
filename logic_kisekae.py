import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# 定義データ
HAIR_STYLES = {
    "元画像のまま": "original hairstyle from IMAGE 1",
    "ゆるふあ巻き": "soft loose wavy curls",
    "ハーフアップ": "elegant half-up style",
    "ツインテール": "playful twin tails",
    "ポニーテール": "neat ponytail",
    "まとめ髪": "sophisticated updo bun",
    "ストレート": "sleek long straight hair"
}

HAIR_COLORS = {
    "元画像のまま": "original hair color from IMAGE 1",
    "ナチュラルブラック": "natural black hair",
    "ダークブラウン": "deep dark brown hair",
    "アッシュベージュ": "ash beige hair color",
    "ミルクティーグレージュ": "soft milk-tea greige hair color",
    "ピンクブラウン": "pinkish brown hair color",
    "ハニーブロンド": "bright honey blonde hair color"
}

STAND_PROMPTS = ["Full body, standing naturally", "Full body, leaning against wall", "Full body, weight on one leg"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting on chair"]

CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual Japanese fashion", "back": "natural skin"},
    "2. 水着（リゾート）": {"en": "Resort swimwear", "back": "healthy skin glow"},
    "3. 部屋着（リラックス）": {"en": "Silk night-fashion", "back": "soft focus"},
    "4. オフィス（スーツ）": {"en": "Business attire", "back": "studio look"},
    "5. コスチューム": {"en": "Themed costume", "back": "meticulous details"},
    "6. 夜の装い（ドレス）": {"en": "Sophisticated evening gown", "back": "dramatic lighting"}
}

# --- 究極の安定生成エンジン ---
def generate_with_retry(client, contents, prompt):
    """エラーの元になる設定をすべて排除し、画像生成のみを命令する"""
    for attempt in range(3):
        try:
            # SDKが拒絶する 'image_generation_config' などを一切含めない
            response = client.models.generate_content(
                model='gemini-3-pro-image-preview',
                contents=contents + [prompt],
                config={"response_modalities": ["IMAGE"]}
            )
            
            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].inline_data.data
            return "SAFETY_BLOCK"
        except Exception as e:
            if "503" in str(e):
                time.sleep(2); continue
            return str(e)
    return "FAILED"

def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, hair_style_en, hair_color_en, cat_key):
    cat_info = CATEGORIES[cat_key]
    prompt = (
        f"CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK.\n"
        f"1. FACE FIDELITY (IMAGE 1): Replicate EXACT face from IMAGE 1. 100% match.\n"
        f"2. HAIR: Style: {hair_style_en}, Color: {hair_color_en}.\n"
        f"3. PHYSICAL: ABSOLUTE BODY VOLUME LOCK. Match IMAGE 1.\n"
        f"4. POSE: {pose_text}. 85mm portrait lens.\n"
        f"5. WARDROBE: {wardrobe_task}\n"
        f"6. RENDER: {bg_prompt}, {cat_info['back']}, soft facial fill-light, 8k, neutral expression."
    )
    return generate_with_retry(client, [identity_part, anchor_part], prompt)

# UI
def show_kisekae_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    if "generated_images" not in st.session_state:
        st.session_state.generated_images = [None] * 4

    st.header("✨ AI KISEKAE (ver 2.89)")
    
    with st.sidebar:
        src = st.file_uploader("キャスト写真", type=['png', 'jpg', 'jpeg'], key="k_src")
        ref = st.file_uploader("衣装参考", type=['png', 'jpg', 'jpeg'], key="k_ref")
        cat = st.selectbox("カテゴリー", list(CATEGORIES.keys()))
        det = st.text_input("衣装仕様書", "サテンの質感")
        h_s = st.selectbox("髪型", list(HAIR_STYLES.keys()))
        h_c = st.selectbox("髪色", list(HAIR_COLORS.keys()))
        run = st.button("✨ 4枚一括生成", type="primary")

    if run and src:
        st.session_state.generated_images = [None] * 4
        status = st.empty()
        
        # Step 1: アンカー
        status.info("🕒 アンカー抽出中...")
        contents = [types.Part.from_bytes(data=ref.getvalue(), mime_type='image/jpeg')] if ref else []
        res_data = generate_with_retry(client, contents, f"Professional product shot of {CATEGORIES[cat]['en']}. {det}.")
        
        if isinstance(res_data, bytes):
            st.session_state.anchor_part = types.Part.from_bytes(data=res_data, mime_type='image/png')
            st.session_state.wardrobe_task = f"Apply design from IMAGE 2. {det}."
            
            # Step 2: 4枚生成
            id_part = types.Part.from_bytes(data=src.getvalue(), mime_type='image/jpeg')
            poses = (STAND_PROMPTS + SIT_PROMPTS)[:4] # 暫定
            for i in range(4):
                status.info(f"🎨 生成中 ({i+1}/4)...")
                res = generate_image_by_text(client, poses[i], id_part, st.session_state.anchor_part, st.session_state.wardrobe_task, "High-end room", HAIR_STYLES[h_s], HAIR_COLORS[h_c], cat)
                if isinstance(res, bytes):
                    st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
            status.empty()
            st.rerun()
        else:
            st.error(f"失敗: {res_data}")

    # 表示
    if any(img is not None for img in st.session_state.generated_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                if st.session_state.generated_images[i]:
                    st.image(st.session_state.generated_images[i], use_container_width=True)
                    buf = io.BytesIO()
                    st.session_state.generated_images[i].save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"img_{i}.jpg", key=f"d_{i}")
                    if st.button("🔄 撮り直し", key=f"r_{i}"):
                        # 撮り直しロジック（略）
                        st.rerun()
