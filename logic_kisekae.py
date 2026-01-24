import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 定義データ（v3.0 黄金律） ---
HAIR_STYLES = {
    "元画像のまま": "original hairstyle from IMAGE 1",
    "ゆるふあ巻き": "soft loose wavy curls",
    "ハーフアップ": "elegant half-up style",
    "ツインテール": "playful twin tails",
    "ポニーテール": "neat ponytail",
    "まとめ髪": "sophisticated updo bun",
    "ストレート": "sleek long straight hair"
}

CATEGORIES = {
    "1. 私服（日常）": "Casual everyday Japanese fashion",
    "2. 水着（リゾート）": "High-end resort swimwear",
    "3. 部屋着（リラックス）": "Silk night-fashion, satin slip",
    "4. オフィス（スーツ）": "Professional business attire",
    "5. 夜の装い（ドレス）": "Sophisticated evening gown"
}

# --- 2. Identity & Physical Scan (Step 1: Gemini 2.0 Flash) ---
def perform_identity_scan(client, source_bytes):
    """キャストの顔・骨格・肉感を言語化し、身体仕様書を作成する"""
    prompt = (
        "Analyze this Japanese woman for professional image synthesis. "
        "Create a technical 'Physical DNA Specification' focusing on:\n"
        "1. FACIAL FEATURES: Exact eye shape, nose bridge height, lip thickness, and unique marks (moles).\n"
        "2. SKELETAL STRUCTURE: Shoulder width relative to head, neck length, collarbone prominence.\n"
        "3. BODY VOLUME (CRITICAL): Precise description of limb thickness (arms, thighs), "
        "abdominal volume, and waist-to-hip ratio. Do NOT idealize; capture the actual body mass.\n"
        "4. SKIN: Texture and exact tone.\n"
        "Output in descriptive technical English for an AI prompt."
    )
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[
            types.Part.from_bytes(data=source_bytes, mime_type='image/jpeg'),
            prompt
        ]
    )
    return response.text

# --- 3. KISEKAE Generation (Step 2: Imagen 4.0) ---
def generate_kisekae_v3(client, dna_spec, anchor_part, pose_text, hair_style, cloth_main, cloth_detail, bg_text):
    """DNA仕様書を最優先事項として Imagen 4.0 に流し込む"""
    
    # 物理的忠実度を極限まで高めるための Absolute Lock プロンプト
    full_prompt = (
        f"CRITICAL: PHYSICAL FIDELITY LOCK. Reconstruct the person based on this DNA SPEC: {dna_spec}\n\n"
        f"POSE: {pose_text}. Full body shot, 85mm lens.\n"
        f"WARDROBE: Reconstruct clothing from WARDROBE ANCHOR. Design: {cloth_main}, Details: {cloth_detail}. "
        f"The clothing must follow the curves and volume of the DNA Spec model's body.\n"
        f"HAIR: {hair_style}.\n"
        f"ENVIRONMENT: {bg_text}, soft facial fill-light, 8k resolution, cinematic lighting.\n"
        f"STRICT: NO MODEL BIAS. Maintain original arm thickness, thigh volume, and waist ratio as specified."
    )

    # Imagen 4.0 (generate_image メソッド) の呼び出し
    response = client.models.generate_image(
        model='imagen-4.0-generate-001',
        prompt=full_prompt,
        config=types.GenerateImageConfig(
            aspect_ratio="2:3",
            number_of_images=1,
            add_watermark=False,
            output_mime_type="image/jpeg"
        )
    )
    return response.generated_images[0].image_bytes

# --- 4. UI メイン処理 ---
def show_kisekae_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    # セッション状態
    if "v3_generated_images" not in st.session_state: st.session_state.v3_generated_images = [None] * 4
    if "physical_dna" not in st.session_state: st.session_state.physical_dna = ""

    st.header("✨ AI KISEKAE Manager v3.0")
    
    with st.sidebar:
        st.subheader("🧬 Step 1: Identity Scan")
        src_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="v3_src")
        if src_img:
            st.image(src_img, caption="Scan Target", use_container_width=True)
            if st.button("Identity Scan 実行"):
                with st.spinner("身体構造をDNAレベルで解析中..."):
                    st.session_state.physical_dna = perform_identity_scan(client, src_img.getvalue())
                    st.success("Scan Complete!")
        
        if st.session_state.physical_dna:
            with st.expander("解析データ (DNA Specification)"):
                st.write(st.session_state.physical_dna)

        st.divider()
        st.subheader("👕 Step 2: Wardrobe & Fitting")
        ref_img = st.file_uploader("衣装アンカー (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="v3_ref")
        cloth_main = st.selectbox("カテゴリー", list(CATEGORIES.keys()))
        cloth_detail = st.text_input("衣装詳細指示", "素材感、特定の色など")
        hair_s = st.selectbox("髪型", list(HAIR_STYLES.keys()))
        bg_text = st.text_input("背景場所", "高級ホテル、夜のテラス")
        
        run_btn = st.button("🚀 v3.0 KISEKAE 実行", type="primary")

    if run_btn and src_img and st.session_state.physical_dna:
        status = st.empty(); progress = st.progress(0)
        
        # ポーズ設定（立ち/座り混合）
        poses = [
            "Standing naturally, facing camera", 
            "Sitting gracefully on a stylish chair", 
            "Standing with weight on one leg, 3/4 view",
            "Relaxed pose, leaning against a wall"
        ]

        # 衣装アンカーの準備
        anchor_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg') if ref_img else None

        for i in range(4):
            status.info(f"🎨 v3.0 高精度生成中 ({i+1}/4)...")
            try:
                img_bytes = generate_kisekae_v3(
                    client, 
                    st.session_state.physical_dna,
                    anchor_part, 
                    poses[i], 
                    HAIR_STYLES[hair_s], 
                    CATEGORIES[cloth_main], 
                    cloth_detail, 
                    bg_text
                )
                st.session_state.v3_generated_images[i] = Image.open(io.BytesIO(img_bytes))
            except Exception as e:
                st.error(f"Error at image {i+1}: {e}")
            progress.progress((i+1)/4)
        
        status.empty(); st.rerun()

    # 表示エリア
    if any(img is not None for img in st.session_state.v3_generated_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                if st.session_state.v3_generated_images[i]:
                    img = st.session_state.v3_generated_images[i]
                    st.image(img, use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"v3_img_{i+1}.jpg", key=f"v3_dl_{i}")
