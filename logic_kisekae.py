import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 定義データ (土台となるプリセット) ---
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

# ポーズの土台
POSE_PRESETS = {
    "おまかせ(ランダム)": "random",
    "立ち: 自然な直立": "Full body, standing naturally",
    "立ち: 壁に寄りかかる": "Full body, leaning against a wall, arms crossed",
    "立ち: 振り返り": "Full body, walking slowly, looking back over shoulder",
    "座り: ソファでリラックス": "Full body, relaxed sitting pose on a sofa",
    "座り: 椅子で脚組み": "Full body, sitting sideways on a chair, crossing legs",
    "座り: 階段に腰掛ける": "Full body, sitting gracefully on steps"
}

# 場所の土台
LOCATION_PRESETS = {
    "高級ホテルの部屋": "Luxury hotel suite, warm ambient lighting",
    "都会のルーフトップバー": "Modern rooftop bar, city night lights, bokeh",
    "リゾートプールサイド": "Infinity pool, sparkling water, sunset glow",
    "お洒落なカフェテラス": "Elegant outdoor cafe, natural sunlight, green plants",
    "大理石の螺旋階段": "Grand marble staircase, dramatic architectural lighting",
    "陽光の差し込む寝室": "Soft morning light in a cozy bedroom, airy atmosphere"
}

CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual everyday Japanese fashion", "back": "natural soft skin"},
    "2. 水着（リゾート）": {"en": "High-end stylish resort swimwear", "back": "healthy skin glow"},
    "3. 部屋着（リラックス）": {"en": "Elegant silk night-fashion, satin slip", "back": "ultra-soft focus"},
    "4. オフィス（スーツ）": {"en": "Professional business attire", "back": "sharp corporate lighting"},
    "5. コスチューム": {"en": "High-quality themed costume", "back": "meticulous details"},
    "6. 夜の装い（ドレス）": {"en": "Sophisticated evening gown", "back": "luxury bokeh"}
}

# --- 2. 生成エンジン (v2.94 安定版を維持) ---
def generate_with_retry(client, contents, prompt, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model='gemini-3-pro-image-preview',
                contents=contents + [prompt],
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE'],
                    safety_settings=[
                        types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')
                    ]
                )
            )
            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].inline_data.data
        except Exception as e:
            if "503" in str(e) and attempt < max_retries:
                time.sleep(2); continue
            return str(e)
    return "FAILED"

def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, hair_style_en, hair_color_en, cat_key):
    cat_info = CATEGORIES[cat_key]
    prompt = (
        f"CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK.\n"
        f"1. FACE FIDELITY (IMAGE 1): Replicate EXACT face from IMAGE 1.\n"
        f"2. HAIR: Style: {hair_style_en}, Color: {hair_color_en}.\n"
        f"3. PHYSICAL: ABSOLUTE BODY VOLUME LOCK. Match IMAGE 1 exactly.\n"
        f"4. POSE: {pose_text}. 2:3 aspect ratio.\n"
        f"5. WARDROBE: {wardrobe_task}\n"
        f"6. RENDER: {bg_prompt}, {cat_info['back']}, soft facial fill-light, 8k, neutral expression."
    )
    return generate_with_retry(client, [identity_part, anchor_part], prompt)

# --- 3. UI メイン処理 ---
def show_kisekae_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    if "generated_images" not in st.session_state: st.session_state.generated_images = [None] * 4
    if "source_bytes" not in st.session_state: st.session_state.source_bytes = None
    if "ref_bytes" not in st.session_state: st.session_state.ref_bytes = None

    st.header("✨ AI KISEKAE Hybrid Manager (v2.94-Plus)")
    
    with st.sidebar:
        # 画像アップロード
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="k_src")
        if src_img:
            st.session_state.source_bytes = src_img.getvalue()
            st.image(src_img, use_container_width=True)
        
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="k_ref")
        if ref_img:
            st.session_state.ref_bytes = ref_img.getvalue()
            st.image(ref_img, use_container_width=True)

        st.divider()

        # 【ハイブリッド入力】
        # 場所の選択と追加指示
        st.subheader("📍 ロケーション")
        loc_base = st.selectbox("土台を選択", list(LOCATION_PRESETS.keys()))
        loc_plus = st.text_input("味付け (追加指示)", placeholder="例: シャンパングラスを持つ")
        final_bg = f"{LOCATION_PRESETS[loc_base]}, {loc_plus}"

        # ポーズの選択と追加指示
        st.subheader("💃 ポーズ設定")
        pose_base = st.selectbox("土台を選択", list(POSE_PRESETS.keys()))
        pose_plus = st.text_input("味付け (追加ポーズ)", placeholder="例: 軽く微笑む")
        
        st.divider()
        
        # その他
        cloth_main = st.selectbox("衣装カテゴリー", list(CATEGORIES.keys()))
        cloth_detail = st.text_input("衣装仕様書", placeholder="例：黒サテン、光沢感")
        hair_s = st.selectbox("💇 髪型", list(HAIR_STYLES.keys()))
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()))
        
        run_btn = st.button("✨ 4枚一括生成", type="primary")

    if run_btn and st.session_state.source_bytes:
        st.session_state.generated_images = [None] * 4
        
        # ポーズの確定ロジック
        base_pose_text = POSE_PRESETS[pose_base]
        
        status = st.empty(); progress = st.progress(0)
        status.info("🕒 アンカー抽出中...")
        
        # アンカー生成
        contents = [types.Part.from_bytes(data=st.session_state.ref_bytes, mime_type='image/jpeg')] if st.session_state.ref_bytes else []
        res_data = generate_with_retry(client, contents, f"Flat lay of {CATEGORIES[cloth_main]['en']}. {cloth_detail}. 1:1 aspect ratio.")
        
        if isinstance(res_data, bytes):
            st.session_state.anchor_part = types.Part.from_bytes(data=res_data, mime_type='image/png')
            st.session_state.wardrobe_task = f"Strictly apply design from IMAGE 2. {cloth_detail}."
            
            identity_part = types.Part.from_bytes(data=st.session_state.source_bytes, mime_type='image/jpeg')
            
            for i in range(4):
                status.info(f"🎨 生成中 ({i+1}/4)...")
                # ポーズがおまかせの場合はランダムに抽選
                current_pose = base_pose_text
                if base_pose_text == "random":
                    current_pose = random.choice(list(POSE_PRESETS.values())[1:])
                
                # 味付けを結合
                final_pose = f"{current_pose}, {pose_plus}"
                
                res = generate_image_by_text(client, final_pose, identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, final_bg, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
                if isinstance(res, bytes):
                    st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
                progress.progress((i+1)/4)
            status.empty(); st.rerun()

    # 表示エリア (v2.94準拠)
    if any(img is not None for img in st.session_state.generated_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                img = st.session_state.generated_images[i]
                if img:
                    st.image(img, use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"img_{i+1}.jpg", "image/jpeg", key=f"dl_{i}")
                    if st.button("🔄 撮り直し", key=f"re_{i}"):
                        # 撮り直し処理 (省略せず維持)
                        with st.spinner("再生成中..."):
                            id_p = types.Part.from_bytes(data=st.session_state.source_bytes, mime_type='image/jpeg')
                            res = generate_image_by_text(client, final_pose, id_p, st.session_state.anchor_part, st.session_state.wardrobe_task, final_bg, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
                            if isinstance(res, bytes):
                                st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
                                st.rerun()
