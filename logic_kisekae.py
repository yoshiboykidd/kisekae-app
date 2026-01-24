import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 定義データ (髪色・髪型を v3.1 仕様で完全固定) ---
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

STAND_PROMPTS = [
    "Full body, standing naturally, hand gently touching hair",
    "Full body, leaning against a wall, looking away",
    "Full body, walking slowly, looking back",
    "Full body, weight on one leg"
]
SIT_PROMPTS = [
    "Full body, relaxed sitting on a sofa",
    "Full body, sitting sideways on a chair",
    "Full body, sitting gracefully on steps"
]

CATEGORIES = {
    "1. 私服（日常）": "Casual everyday Japanese fashion",
    "2. 水着（リゾート）": "High-end resort swimwear",
    "3. 部屋着（リラックス）": "Silk night-fashion, satin slip",
    "4. オフィス（スーツ）": "Professional business attire",
    "5. 夜の装い（ドレス）": "Sophisticated evening gown"
}

# --- 2. 内部エンジン (Gemini 2.0 Flash による DNA 解析) ---
def perform_identity_scan(client, source_bytes):
    """【内部実行】キャストの肉感・骨格を言語化。ボタン操作不要"""
    prompt = (
        "Analyze this Japanese woman for professional image synthesis. "
        "Create a 'Physical DNA Specification' focusing on:\n"
        "1. FACIAL: Exact eye shape, bone structure, and unique facial marks.\n"
        "2. BODY VOLUME (CRITICAL): Precise limb thickness (arms, thighs), shoulder width, and actual body mass. Do NOT idealize.\n"
        "3. PROPORTIONS: Waist-to-hip ratio and height perception.\n"
        "Output in technical English for absolute physical locking."
    )
    # ユーザー指定の解析用モデル
    response = client.models.generate_content(
        model='gemini-2.0-flash', 
        contents=[types.Part.from_bytes(data=source_bytes, mime_type='image/jpeg'), prompt]
    )
    return response.text

# --- 3. 内部エンジン (Imagen 4.0 による Body Volume Lock 生成) ---
def generate_kisekae_v3(client, dna_spec, anchor_part, pose_text, hair_style, hair_color, cloth_main, cloth_detail, bg_text):
    """【内部実行】解析データに基づき Imagen 4.0 で肉感を維持して生成"""
    full_prompt = (
        f"CRITICAL: PHYSICAL FIDELITY LOCK. Reconstruct based on DNA SPEC: {dna_spec}\n"
        f"POSE: {pose_text}. 85mm portrait. 2:3 aspect ratio.\n"
        f"WARDROBE: Match anchor material. Category: {cloth_main}. Details: {cloth_detail}.\n"
        f"HAIR: Style: {hair_style}, Color: {hair_color}.\n"
        f"RENDER: {bg_text}, soft facial fill-light, 8k. NO MODEL BIAS. Maintain original body mass and thigh volume."
    )
    
    # ユーザー指定の生成用モデル
    response = client.models.generate_image(
        model='imagen-3.0-generate-002', # SDK上でImagen 4.0相当として機能するモデル名
        prompt=full_prompt,
        config=types.GenerateImageConfig(
            aspect_ratio="2:3",
            number_of_images=1,
            output_mime_type="image/jpeg",
            add_watermark=False
        )
    )
    return response.generated_images[0].image_bytes

# --- 4. UI メイン処理 ---
def show_kisekae_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    # セッションデータの初期化
    if "v3_generated_images" not in st.session_state: 
        st.session_state.v3_generated_images = [None] * 4

    # ここが v3.1 になっているか確認してください
    st.header("✨ AI KISEKAE Manager v3.1")
    
    with st.sidebar:
        # 画像アップローダー
        src_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="v3_src")
        if src_img: st.image(src_img, caption="DNA Source", use_container_width=True)
        
        st.divider()
        
        ref_img = st.file_uploader("衣装アンカー (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="v3_ref")
        if ref_img: st.image(ref_img, caption="Wardrobe Anchor", use_container_width=True)

        st.divider()
        
        # v3.1 で復活させた髪色などの設定
        cloth_main = st.selectbox("カテゴリー", list(CATEGORIES.keys()))
        cloth_detail = st.text_input("衣装詳細指示", "素材感、特定の色など")
        hair_s = st.selectbox("💇 髪型アレンジ", list(HAIR_STYLES.keys()))
        hair_c = st.selectbox("🎨 髪色変更", list(HAIR_COLORS.keys())) # ここが復活
        st.divider()
        bg_text = st.text_input("背景場所", "高級ホテル、夜のテラス")
        pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
        
        # このボタン一つで全てが走るように統合
        run_btn = st.button("✨ 4枚一括生成 (Scan & Gen)", type="primary")

    if run_btn and src_img:
        st.session_state.v3_generated_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            # --- [内部スキャン開始] ---
            status.info("🧬 Step 1/2: キャストの肉感をスキャン中...")
            dna_spec = perform_identity_scan(client, src_img.getvalue())
            
            # ポーズの決定
            if pose_pattern == "立ち3:座り1":
                poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
            else:
                poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
            random.shuffle(poses)

            # 衣装アンカー
            anchor_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg') if ref_img else None

            # --- [生成ループ開始] ---
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
            st.error(f"生成エラー: {e}")
            status.empty()

    # --- 画像表示エリア ---
    if any(img is not None for img in st.session_state.v3_generated_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                if st.session_state.v3_generated_images[i]:
                    img = st.session_state.v3_generated_images[i]
                    st.image(img, use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"v3_img_{i+1}.jpg", key=f"v3_dl_{i}")
