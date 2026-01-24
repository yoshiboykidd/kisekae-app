import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. [DNA定義] 髪型・髪色データ ---
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
SIT_PROMPTS = ["Full body, sitting on a sofa", "Full body, sitting on steps"]

CATEGORIES = {
    "1. 私服（日常）": "Casual everyday Japanese fashion",
    "2. 水着（リゾート）": "High-end resort swimwear",
    "3. 部屋着（リラックス）": "Silk night-fashion, satin slip",
    "4. オフィス（スーツ）": "Professional business attire",
    "5. 夜の装い（ドレス）": "Sophisticated evening gown"
}

# --- 2. [解析] Identity & Physical Scan (Gemini 2.0 Flash) ---
def perform_identity_scan(client, source_bytes):
    """キャストの肉感を言語化。現在のAPIで最も安定している Gemini 2.0 Flash を使用"""
    prompt = (
        "Technical Physical Analysis for AI Synthesis:\n"
        "1. Identify the exact facial DNA of this Japanese woman.\n"
        "2. BODY VOLUME LOCK: Describe the limb thickness, shoulder width, and actual body mass in detail.\n"
        "3. Ensure the description captures realistic physical presence without idealization.\n"
        "Output as a technical specification in English."
    )
    # Gemini 2.0 Flash は 404 になりにくい安定モデル
    response = client.models.generate_content(
        model='gemini-2.0-flash', 
        contents=[types.Part.from_bytes(data=source_bytes, mime_type='image/jpeg'), prompt]
    )
    return response.text

# --- 3. [生成] KISEKAE Generation (Standard Imagen 3/4) ---
def generate_kisekae_v3(client, dna_spec, anchor_part, pose_text, hair_style, hair_color, cloth_main, cloth_detail, bg_text):
    """肉感(Body Volume)を維持して生成。モデル名をエイリアス(imagen-3)に変更"""
    full_prompt = (
        f"CRITICAL: PHYSICAL FIDELITY LOCK. Reconstruct person based on: {dna_spec}\n"
        f"POSE: {pose_text}. 85mm portrait. 2:3 aspect ratio.\n"
        f"WARDROBE: Re-tailor from anchor: {cloth_main}. Details: {cloth_detail}.\n"
        f"HAIR: Style: {hair_style}, Color: {hair_color}.\n"
        f"RENDER: {bg_text}, soft facial fill-light, 8k. NO MODEL BIAS. Maintain original body mass."
    )
    
    # 修正：404を回避するため、最も汎用的なエイリアス 'imagen-3' を使用
    # 環境によっては 'imagen-3.0-generate-001' よりもこちらが優先されます
    response = client.models.generate_image(
        model='imagen-3', 
        prompt=full_prompt,
        config=types.GenerateImageConfig(
            aspect_ratio="2:3",
            number_of_images=1,
            output_mime_type="image/jpeg"
        )
    )
    return response.generated_images[0].image_bytes

# --- 4. UI メイン処理 ---
def show_kisekae_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    if "v3_generated_images" not in st.session_state: 
        st.session_state.v3_generated_images = [None] * 4

    st.header("✨ AI KISEKAE Manager v3.1.3")
    
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
            # Step 1: 解析
            status.info("🧬 Step 1/2: 身体構造をスキャン中...")
            dna_spec = perform_identity_scan(client, src_img.getvalue())
            
            # ポーズ決定
            poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2) # 暫定
            anchor_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg') if ref_img else None

            # Step 2: 生成
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
            st.info("💡 対策: モデル名を 'imagen-3' に変更しました。もしこれでも 404 が出る場合は、APIがまだ Imagen 生成をサポートしていない可能性があります。")
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
