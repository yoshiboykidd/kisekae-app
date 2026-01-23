import streamlit as st
from google import genai
# types は Part 等の基本要素にのみ使用し、Config系には使用しない
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 定義データ (黄金律・髪型順序厳守) ---
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
    "ミルクティーグレージュ": "milk-tea greige hair color",
    "ピンクブラウン": "pinkish brown hair color",
    "ハニーブロンド": "bright honey blonde hair color"
}

STAND_PROMPTS = ["Full body, standing naturally", "Full body, leaning against a wall", "Full body, walking slowly", "Full body, weight on one leg"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways on chair", "Full body, sitting on steps"]

CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual Japanese fashion", "back_prompt": "natural skin, daylight"},
    "2. 水着（リゾート）": {"en": "Resort swimwear", "back_prompt": "healthy skin glow"},
    "3. 部屋着（リラックス）": {"en": "Silk night-fashion", "back_prompt": "soft focus, rim light"},
    "4. オフィス（スーツ）": {"en": "Business professional attire", "back_prompt": "studio look"},
    "5. コスチューム": {"en": "Themed costume", "back_prompt": "meticulous details"},
    "6. 夜の装い（ドレス）": {"en": "Sophisticated evening gown", "back_prompt": "dramatic lighting"}
}

# --- 2. 生成コア関数 (ver 2.81: Version-Agnostic Dict Config) ---
def generate_with_retry(client, contents, prompt, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            # ★ 修正：types.ImageGenerationConfig 等の「クラス」を使わず「辞書」で渡す
            # これにより SDK のバージョンによる名前変更エラーを回避
            gen_config = {
                "response_modalities": ["IMAGE"],
                "safety_settings": [
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}
                ],
                "image_generation_config": {
                    "aspect_ratio": "2:3",
                    "number_of_images": 1
                }
            }
            
            response = client.models.generate_content(
                model='gemini-3-pro-image-preview',
                contents=contents + [prompt],
                config=gen_config
            )
            
            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].inline_data.data
            return "SAFETY_BLOCK"
        except Exception as e:
            if "503" in str(e) and attempt < max_retries:
                time.sleep(2); continue
            return str(e)
    return "RETRY_FAILED"

def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, hair_style_en, hair_color_en, cat_key):
    cat_info = CATEGORIES[cat_key]
    prompt = (
        f"CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK.\n"
        f"1. FACE FIDELITY (IMAGE 1): Replicate the EXACT facial structure of IMAGE 1. 100% identity match.\n"
        f"2. HAIR: Style: {hair_style_en}, Color: {hair_color_en}.\n"
        f"3. PHYSICAL: Match exact body mass of IMAGE 1.\n"
        f"4. POSE: {pose_text}. 85mm portrait.\n"
        f"5. WARDROBE: {wardrobe_task}\n"
        f"6. RENDER: {bg_prompt}, {cat_info['back_prompt']}, soft facial fill-light, 8k, neutral expression."
    )
    return generate_with_retry(client, [identity_part, anchor_part], prompt)

def show_kisekae_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    if "generated_images" not in st.session_state: st.session_state.generated_images = [None] * 4

    st.header("✨ AI KISEKAE Main System (v2.81)")
    with st.sidebar:
        source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="k_src")
        ref_img = st.file_uploader("衣装参考 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="k_ref")
        st.divider()
        cloth_main = st.selectbox("衣装カテゴリー", list(CATEGORIES.keys()))
        cloth_detail = st.text_input("衣装仕様書", placeholder="例：黒サテン")
        hair_s = st.selectbox("💇 髪型アレンジ", list(HAIR_STYLES.keys()))
        hair_c = st.selectbox("🎨 髪色変更", list(HAIR_COLORS.keys()))
        st.divider()
        bg_text = st.text_input("場所", "高級ホテル")
        time_of_day = st.radio("時間帯", ["昼 (Daylight)", "夕方 (Golden Hour)", "夜 (Night)"])
        pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
        run_btn = st.button("✨ 4枚一括生成", type="primary")

    if run_btn and source_img:
        st.session_state.generated_images = [None] * 4
        time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "warm sunset glow", "夜 (Night)": "night lights"}
        st.session_state.final_bg_prompt = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh"
        
        if pose_pattern == "立ち3:座り1": poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
        else: poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
        random.shuffle(poses)
        st.session_state.current_pose_texts = poses

        status = st.empty(); progress = st.progress(0)
        status.info("🕒 Step 1/2: 衣装アンカー抽出中...")
        
        anchor_prompt = f"Professional product shot of {CATEGORIES[cloth_main]['en']} material. {cloth_detail}. Textile scan."
        contents = [types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')] if ref_img else []
        res_data = generate_with_retry(client, contents, anchor_prompt)
        
        if isinstance(res_data, bytes):
            st.session_state.anchor_part = types.Part.from_bytes(data=res_data, mime_type='image/png')
            st.session_state.wardrobe_task = f"Strictly apply design from IMAGE 2. {cloth_detail}."
            
            identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')
            for i in range(4):
                status.info(f"🎨 Step 2/2: 生成中 ({i+1}/4)...")
                res = generate_image_by_text(client, st.session_state.current_pose_texts[i], identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
                if isinstance(res, bytes): st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
                progress.progress((i+1)/4)
            status.empty(); st.rerun()
        else: st.error(f"アンカー失敗: {res_data}")

    # 画像表示
    if any(img is not None for img in st.session_state.generated_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                img = st.session_state.generated_images[i]
                if img:
                    st.image(img, use_container_width=True)
                    c1, c2 = st.columns(2)
                    with c1:
                        buf = io.BytesIO(); img.save(buf, format="JPEG")
                        st.download_button("💾 保存", buf.getvalue(), f"img_{i+1}.jpg", "image/jpeg", key=f"dl_{i}")
                    with c2:
                        if st.button("🔄 撮り直し", key=f"re_{i}"):
                            with st.spinner("再生成中..."):
                                id_p = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')
                                res = generate_image_by_text(client, st.session_state.current_pose_texts[i], id_p, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
                                if isinstance(res, bytes):
                                    st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
                                    st.rerun()
