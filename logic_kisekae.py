import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 定義データ (ポーズ被りを防ぐための豊富なプール) ---
STAND_POOL = [
    "Full body, standing naturally, looking at camera",
    "Full body, walking slowly towards camera",
    "Full body, leaning against a wall, adjusting hair",
    "Full body, 3/4 view, hand on hip, looking away",
    "Full body, standing with weight on one leg, elegant silhouette"
]

SIT_POOL = [
    "Full body, relaxed sitting pose on a sofa",
    "Full body, sitting sideways on a chair, crossing legs",
    "Full body, sitting gracefully on steps, hands on lap",
    "Full body, sitting on a stool, looking over shoulder"
]

HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft loose wavy curls", "ハーフアップ": "half-up style", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo bun", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "original hair color", "ナチュラルブラック": "natural black", "ダークブラウン": "dark brown", "アッシュベージュ": "ash beige", "ミルクティーグレージュ": "milk-tea greige", "ピンクブラウン": "pinkish brown"}
LOCATION_PRESETS = {"高級ホテルの部屋": "Luxury hotel suite", "都会のルーフトップバー": "Rooftop bar, city lights", "リゾートプールサイド": "Infinity pool, sunset", "お洒落なカフェテラス": "Outdoor cafe terrace", "大理石の螺旋階段": "Grand marble staircase", "陽光の差し込む寝室": "Cozy sunlit bedroom"}
CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual fashion", "back": "natural soft skin"},
    "2. 水着（リゾート）": {"en": "High-end swimwear", "back": "healthy skin glow"},
    "3. 部屋着（リラックス）": {"en": "Silk night-fashion", "back": "soft focus"},
    "4. オフィス（スーツ）": {"en": "Business attire", "back": "sharp lighting"},
    "5. 夜の装い（ドレス）": {"en": "Sophisticated evening gown", "back": "luxury bokeh"}
}

# --- 2. 生成エンジン (v2.94 安定版ロジック) ---
def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, hair_s, hair_c, cat_key):
    cat_info = CATEGORIES[cat_key]
    prompt = (
        f"CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK.\n"
        f"1. FACE FIDELITY (IMAGE 1): Replicate EXACT face from IMAGE 1.\n"
        f"2. HAIR: Style: {hair_s}, Color: {hair_c}.\n"
        f"3. PHYSICAL: ABSOLUTE BODY VOLUME LOCK. Match IMAGE 1 volume exactly.\n"
        f"4. POSE: {pose_text}. 2:3 aspect ratio.\n"
        f"5. WARDROBE: {wardrobe_task}\n"
        f"6. RENDER: {bg_prompt}, {cat_info['back']}, soft fill-light, 8k, neutral expression."
    )
    response = client.models.generate_content(
        model='gemini-3-pro-image-preview',
        contents=[identity_part, anchor_part, prompt],
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE'],
            safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')]
        )
    )
    return response.candidates[0].content.parts[0].inline_data.data

# --- 3. UI メイン処理 ---
def show_kisekae_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    if "generated_images" not in st.session_state: st.session_state.generated_images = [None] * 4
    if "current_poses" not in st.session_state: st.session_state.current_poses = [None] * 4
    if "source_bytes" not in st.session_state: st.session_state.source_bytes = None
    if "ref_bytes" not in st.session_state: st.session_state.ref_bytes = None

    st.header("✨ AI KISEKAE Manager (v2.99)")
    
    with st.sidebar:
        # 画像アップローダー
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="k_src")
        if src_img:
            st.session_state.source_bytes = src_img.getvalue()
            st.image(src_img, use_container_width=True)
        
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="k_ref")
        if ref_img:
            st.session_state.ref_bytes = ref_img.getvalue()
            st.image(ref_img, use_container_width=True)

        st.divider()

        # 【ここが重要：比率設定の復活】
        st.subheader("💃 ポーズ構成")
        pose_pattern = st.radio("比率設定", ["立ち3:座り1", "立ち2:座り2"], index=0)
        pose_plus = st.text_input("追加指示 (味付け)", placeholder="例: gentle smile")

        st.divider()

        # 場所・衣装・髪
        loc_base = st.selectbox("ロケーション", list(LOCATION_PRESETS.keys()))
        loc_plus = st.text_input("場所の微調整", placeholder="例: 窓際")
        final_bg = f"{LOCATION_PRESETS[loc_base]}, {loc_plus}"

        cloth_main = st.selectbox("衣装カテゴリー", list(CATEGORIES.keys()))
        cloth_detail = st.text_input("衣装仕様書", placeholder="例：サテン")
        hair_s = st.selectbox("💇 髪型", list(HAIR_STYLES.keys()))
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()))
        
        run_btn = st.button("✨ 4枚一括生成", type="primary")

    if run_btn and st.session_state.source_bytes:
        # --- [比率に基づいて、プールから被りなしで抽出] ---
        if pose_pattern == "立ち3:座り1":
            selected_stands = random.sample(STAND_POOL, 3) # 重複なしの立ち3種
            selected_sits = random.sample(SIT_POOL, 1)      # 重複なしの座り1種
        else:
            selected_stands = random.sample(STAND_POOL, 2) # 重複なしの立ち2種
            selected_sits = random.sample(SIT_POOL, 2)      # 重複なしの座り2種
        
        final_pool = selected_stands + selected_sits
        random.shuffle(final_pool) # 表示位置をランダムに
        st.session_state.current_poses = [f"{p}, {pose_plus}" for p in final_pool]

        # 生成処理
        status = st.empty(); progress = st.progress(0)
        status.info("🕒 衣装アンカー作成中...")
        
        # アンカー作成
        contents = [types.Part.from_bytes(data=st.session_state.ref_bytes, mime_type='image/jpeg')] if st.session_state.ref_bytes else []
        res_data = generate_image_by_text(client, "Flat lay of clothing", types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg'), contents[0] if contents else None, f"Professional flat lay of {cloth_detail}", "Studio lighting", "original", "original", cloth_main)
        st.session_state.anchor_part = types.Part.from_bytes(data=res_data, mime_type='image/png')
        
        id_part = types.Part.from_bytes(data=st.session_state.source_bytes, mime_type='image/jpeg')
        for i in range(4):
            status.info(f"🎨 生成中 ({i+1}/4)...")
            res = generate_image_by_text(client, st.session_state.current_poses[i], id_part, st.session_state.anchor_part, f"Apply design: {cloth_detail}", final_bg, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
            st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
            progress.progress((i+1)/4)
        status.empty(); st.rerun()

    # 表示エリア
    if any(img is not None for img in st.session_state.generated_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                if st.session_state.generated_images[i]:
                    st.image(st.session_state.generated_images[i], use_container_width=True)
                    # ダウンロード・撮り直しボタンは v2.98 と同様に完備
