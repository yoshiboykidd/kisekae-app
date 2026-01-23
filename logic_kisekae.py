import streamlit as st
from google import genai
from google.genai import types  # Part等の基本データ型には使用
from PIL import Image
import io
import time
import random

# --- 1. 絶対不変の定義データ (黄金律 & 髪型順序) ---
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

STAND_PROMPTS = [
    "Full body portrait, standing naturally, hand gently touching hair",
    "Full body portrait, leaning against a wall, arms casually crossed",
    "Full body portrait, walking slowly, looking back over shoulder",
    "Full body portrait, standing with weight on one leg, one hand on hip"
]
SIT_PROMPTS = [
    "Full body portrait, relaxed sitting pose on a sofa, looking at camera",
    "Full body portrait, sitting sideways on a chair, leaning on the backrest",
    "Full body portrait, sitting gracefully on steps, hands resting in lap"
]

CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual everyday Japanese fashion", "back_prompt": "natural soft skin, soft daylight"},
    "2. 水着（リゾート）": {"en": "High-end stylish resort swimwear", "back_prompt": "healthy skin glow, vibrant summer lighting"},
    "3. 部屋着（リラックス）": {"en": "Elegant silk night-fashion, satin camisole-style", "back_prompt": "ultra-soft focus, warm rim lighting"},
    "4. オフィス（スーツ）": {"en": "Elegant business professional attire", "back_prompt": "sharp corporate lighting, professional studio look"},
    "5. コスチューム": {"en": "High-quality themed costume, professional uniform", "back_prompt": "meticulous details, professional strobe"},
    "6. 夜の装い（ドレス）": {"en": "Sophisticated evening gown", "back_prompt": "luxury bokeh, dramatic lighting, soft facial fill-light"}
}

# --- 2. 安定化生成エンジン (辞書型設定による Attribute Error 回避) ---
def generate_with_retry(client, contents, prompt, aspect_ratio="2:3", max_retries=2):
    """
    クラス名(ImageGenerationConfig等)を使わず辞書で設定を渡すことで、
    SDKのバージョン差異によるクラッシュを完全に回避する
    """
    for attempt in range(max_retries + 1):
        try:
            # 辞書形式で設定を構築（最も互換性が高い）
            gen_config = {
                "response_modalities": ["IMAGE"],
                "image_generation_config": {
                    "aspect_ratio": aspect_ratio,
                    "number_of_images": 1
                },
                "safety_settings": [
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}
                ]
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
    """黄金律に基づくプロンプト構築"""
    cat_info = CATEGORIES[cat_key]
    prompt = (
        f"CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK.\n"
        f"1. FACE FIDELITY (IMAGE 1): Replicate the EXACT facial structure of IMAGE 1. 100% identity match.\n"
        f"2. HAIR CUSTOMIZATION: Style: {hair_style_en}, Color: {hair_color_en}.\n"
        f"3. PHYSICAL FIDELITY: [STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK]. Match body mass of IMAGE 1.\n"
        f"4. POSE & COMPOSITION: {pose_text}. 85mm portrait lens.\n"
        f"5. WARDROBE (IMAGE 2): {wardrobe_task}\n"
        f"6. RENDER: {bg_prompt}, {cat_info['back_prompt']}, soft facial fill-light, 8k, neutral expression."
    )
    return generate_with_retry(client, [identity_part, anchor_part], prompt, aspect_ratio="2:3")

# --- 3. UI メイン処理 ---
def show_kisekae_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    if "generated_images" not in st.session_state:
        st.session_state.generated_images = [None] * 4
    if "current_pose_texts" not in st.session_state:
        st.session_state.current_pose_texts = [None] * 4

    st.header("✨ AI KISEKAE Main System (v2.84)")
    
    with st.sidebar:
        source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="kise_src")
        ref_img = st.file_uploader("衣装参考 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="kise_ref")
        st.divider()
        cloth_main = st.selectbox("衣装カテゴリー", list(CATEGORIES.keys()))
        cloth_detail = st.text_input("衣装仕様書", placeholder="例：黒サテン、光沢感")
        hair_s = st.selectbox("💇 髪型アレンジ", list(HAIR_STYLES.keys()))
        hair_c = st.selectbox("🎨 髪色変更", list(HAIR_COLORS.keys()))
        st.divider()
        bg_text = st.text_input("場所", "高級ホテルの部屋")
        time_of_day = st.radio("時間帯", ["昼 (Daylight)", "夕方 (Golden Hour)", "夜 (Night)"])
        pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
        run_btn = st.button("✨ 4枚一括生成", type="primary")

    if run_btn and source_img:
        st.session_state.generated_images = [None] * 4
        time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "warm sunset glow", "夜 (Night)": "night lights"}
        st.session_state.final_bg_prompt = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh"
        
        # ポーズ決定
        if pose_pattern == "立ち3:座り1":
            poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
        else:
            poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
        random.shuffle(poses)
        st.session_state.current_pose_texts = poses

        status = st.empty(); progress = st.progress(0)

        # Step 1: 衣装アンカー
        status.info("🕒 Step 1/2: 衣装設計図（アンカー）を抽出中...")
        anchor_prompt = f"Professional product photography of {CATEGORIES[cloth_main]['en']} material. {cloth_detail}. Textile scan quality."
        contents = [types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')] if ref_img else []
        res_data = generate_with_retry(client, contents, anchor_prompt, aspect_ratio="1:1")
        
        if isinstance(res_data, bytes):
            st.session_state.anchor_part = types.Part.from_bytes(data=res_data, mime_type='image/png')
            st.session_state.wardrobe_task = f"Strictly replicate the design from IMAGE 2. {cloth_detail}."
            
            # Step 2: 4枚生成
            identity_part = types.Part.from_bytes(data=source_img.getvalue(),
