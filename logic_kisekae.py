import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 定義データ (黄金律 DNA) ---
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

STAND_PROMPTS = ["Full body, standing naturally", "Full body, walking towards camera", "Full body, side profile"]
SIT_PROMPTS = ["Full body, relaxed sitting on a sofa", "Full body, sitting on steps"]

CATEGORIES = {
    "1. 私服（日常）": "Casual everyday Japanese fashion",
    "2. 水着（リゾート）": "High-end resort swimwear",
    "3. 部屋着（リラックス）": "Silk night-fashion, satin slip",
    "4. オフィス（スーツ）": "Professional business attire",
    "5. 夜の装い（ドレス）": "Sophisticated evening gown"
}

# --- 2. 内部エンジン: Identity Scan (Gemini 2.0 Flash) ---
def perform_identity_scan(client, source_bytes):
    """【安定動作】キャストの肉感・骨格を言語化"""
    prompt = (
        "Analyze this Japanese woman for professional image synthesis. "
        "Create a technical 'Physical DNA Specification' focusing on:\n"
        "1. FACIAL: Eye shape, bone structure, unique facial marks.\n"
        "2. BODY VOLUME (CRITICAL): Precise limb thickness (arms, thighs), actual body mass. Do NOT idealize.\n"
        "3. PROPORTIONS: Waist-to-hip ratio and muscle/softness balance.\n"
        "Output in descriptive technical English."
    )
    response = client.models.generate_content(
        model='gemini-2.0-flash', 
        contents=[types.Part.from_bytes(data=source_bytes, mime_type='image/jpeg'), prompt]
    )
    return response.text

# --- 3. 生成エンジン: KISEKAE (アンカー君と同じ安定方式) ---
def generate_kisekae_v3(client, dna_spec, anchor_part, pose_text, hair_style, hair_color, cloth_main, cloth_detail, bg_text):
    """【404回避】アンカー製作君と同じ gemini-3-pro-image-preview を使用"""
    full_prompt = (
        f"CRITICAL: PHYSICAL FIDELITY LOCK. Reconstruct based on DNA SPEC: {dna_spec}\n"
        f"POSE: {pose_text}. 85mm portrait. 2:3 aspect ratio.\n"
        f"WARDROBE: Follow clothing anchor. Category: {cloth_main}. Details: {cloth_detail}.\n"
        f"HAIR: Style: {hair_style}, Color: {hair_color}.\n"
        f"RENDER: {bg_text}, soft facial fill-light, 8k. NO MODEL BIAS. Maintain original body mass and thigh volume."
    )
    
    # generate_image ではなく generate_content を使うことで 404 を回避
    response = client.models.generate_content(
        model='gemini-3-pro-image-preview',
        contents=[anchor_part, full_prompt] if anchor_part else [full_prompt],
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE'],
            safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')]
        )
    )
    
    if response.candidates and response.candidates[0].content.parts:
        return response.candidates[0].content.parts[0].inline_data.data
    raise Exception("画像生成に失敗しました（セーフティフィルタ等の可能性）")

# --- 4. UI メイン処理 ---
def show_kisekae_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    if "v3_generated_images" not in st.session_state: 
        st.session_state.v3_generated_images = [None] * 4

    st.header("✨ AI KISEKAE Manager v3.1.5 (Stable)")
    
    with st.sidebar:
        src_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="v3_src")
        if src_img: st.image(src_img, caption="DNA Source", use_container_width=True)
        
        st.divider()
        ref_img = st.file_uploader("衣装アンカー (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="v3_ref")
        
        cloth_main = st.selectbox("カテゴリー", list(CATEGORIES.keys()))
        cloth_detail = st.text_input("衣装詳細指示", "素材感、色、装飾など")
        hair_s = st.selectbox("💇 髪型アレンジ", list(HAIR_STYLES.keys()))
        hair_c = st.selectbox("🎨 髪色変更", list(HAIR_COLORS.keys()))
        bg_text = st.text_input("背景場所", "高級ホテル")
        pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
        
        run_btn = st.button("✨ 4枚一括生成 (Scan & Gen)", type="primary")

    if run_btn and src_img:
        st.session_state.v3_generated_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            # Step 1: 解析 (Gemini 2.0 Flash)
            status.info("🧬 Step 1/2: 身体構造をスキャン中...")
            dna_spec = perform_identity_scan(client, src_img.getvalue())
            
            # ポーズ決定
            if pose_pattern == "立ち3:座り1":
                poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
            else:
                poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
            random.shuffle(poses)

            # 衣装アンカー
            anchor_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg') if ref_img else None

            # Step 2: 生成 (Gemini-Integrated Image Gen)
            for i in range(4):
                status.info(f"🎨 Step 2/2: Body Volume Lock 生成中 ({i+1}/4)...")
                img_bytes = generate_kisekae_v3(
                    client, dna_spec, anchor_part, poses[i], 
                    HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], 
                    CATEGORIES[cloth_main], cloth_detail, bg_text
                )
                st.session_state.v3_generated_images[i] = Image.open(io.BytesIO(img_bytes))
                progress.progress((i+1)/4)
            
            status.empty(); st.rerun()

        except Exception as e:
            st.error(f"⚠️ 生成エラー: {e}")
            status.empty()

    # --- 表示エリア ---
    if any(img is not None for img in st.session_state.v3_generated_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                if st.session_state.v3_generated_images[i]:
                    img = st.session_state.v3_generated_images[i]
                    st.image(img, use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"v3_img_{i+1}.jpg", key=f"v3_dl_{i}")
