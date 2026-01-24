import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 定義データ (ポーズ被り防止プール & 厳選7プリセット) ---
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

LOCATION_PRESETS = {
    "（自由記載のみ）": "",
    "街角のオープンカフェ": "at an elegant open-air street cafe with outdoor seating and plants",
    "洗練された並木道": "on a refined tree-lined boulevard with modern architecture",
    "お洒落なセレクトショップ": "inside a stylish select shop with large mirrors and clothing displays",
    "ルーフトップテラス": "on a spacious rooftop terrace with a wide panoramic background",
    "都会を一望するバーカウンター": "at a sleek bar counter overlooking the city skyline",
    "住宅街の静かな公園": "in a quiet park in a peaceful residential neighborhood with benches",
    "地元の小さな商店街": "at a local small shopping street with nostalgic shop signs"
}

HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft loose wavy curls", "ハーフアップ": "half-up style", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo bun", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "original hair color", "ナチュラルブラック": "natural black", "ダークブラウン": "dark brown", "アッシュベージュ": "ash beige", "ミルクティーグレージュ": "milk-tea greige", "ピンクブラウン": "pinkish brown"}

CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual fashion", "back": "natural soft skin"},
    "2. 水着（リゾート）": {"en": "High-end swimwear", "back": "healthy skin glow"},
    "3. 部屋着（リラックス）": {"en": "Silk night-fashion, satin slip", "back": "ultra-soft focus"},
    "4. オフィス（スーツ）": {"en": "Professional business attire", "back": "sharp lighting"},
    "5. 夜の装い（ドレス）": {"en": "Sophisticated evening gown", "back": "luxury bokeh"}
}

# --- 2. 生成エンジン (v2.94 準拠の安定ロジック) ---
def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, hair_s, hair_c, cat_key):
    cat_info = CATEGORIES[cat_key]
    prompt = (
        f"CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK.\n"
        f"1. FACE FIDELITY (IMAGE 1): Replicate EXACT face from IMAGE 1.\n"
        f"2. HAIR: Style: {hair_s}, Color: {hair_c}.\n"
        f"3. PHYSICAL: ABSOLUTE BODY VOLUME LOCK. Match IMAGE 1 volume exactly.\n"
        f"4. POSE: {pose_text}. 2:3 aspect ratio.\n"
        f"5. WARDROBE: {wardrobe_task}\n"
        f"6. RENDER: {bg_prompt}, {cat_info['back']}, soft facial fill-light, 8k, neutral expression."
    )
    # 安定の generate_content 方式
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
    
    # セッション状態の初期化
    if "generated_images" not in st.session_state: st.session_state.generated_images = [None] * 4
    if "current_poses" not in st.session_state: st.session_state.current_poses = [None] * 4
    if "final_bg_prompt" not in st.session_state: st.session_state.final_bg_prompt = ""
    if "anchor_part" not in st.session_state: st.session_state.anchor_part = None
    if "wardrobe_task" not in st.session_state: st.session_state.wardrobe_task = ""
    if "source_bytes" not in st.session_state: st.session_state.source_bytes = None
    if "ref_bytes" not in st.session_state: st.session_state.ref_bytes = None

    st.header("✨ AI KISEKAE Manager v3.00")
    
    with st.sidebar:
        # 画像アップローダー
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="k_src")
        if src_img:
            st.session_state.source_bytes = src_img.getvalue()
            st.image(src_img, caption="DNA Source", use_container_width=True)
        
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="k_ref")
        if ref_img:
            st.session_state.ref_bytes = ref_img.getvalue()
            st.image(ref_img, caption="Wardrobe Source", use_container_width=True)

        st.divider()

        # 💃 ポーズ構成
        st.subheader("💃 ポーズ構成")
        pose_pattern = st.radio("比率設定", ["立ち3:座り1", "立ち2:座り2"], index=0)
        pose_plus = st.text_input("追加指示 (味付け)", placeholder="例: gentle smile")

        st.divider()

        # 📍 ロケーション & 🕒 時間帯
        st.subheader("📍 ロケーション設定")
        loc_free = st.text_input("場所の自由記載", placeholder="例: 窓際、雨の演出")
        loc_preset = st.selectbox("プリセットから選ぶ", list(LOCATION_PRESETS.keys()))
        time_of_day = st.radio("時間帯", ["昼 (Daylight)", "夕 (Golden Hour)", "夜 (Night)"])
        
        time_mods = {
            "昼 (Daylight)": "bright natural daylight, high-key lighting",
            "夕 (Golden Hour)": "warm golden hour glow, sunset lighting",
            "夜 (Night)": "cinematic night atmosphere, city lights, neon bokeh"
        }
        
        # 自由記載、プリセット、時間を融合
        st.session_state.final_bg_prompt = f"{loc_free}, {LOCATION_PRESETS[loc_preset]}, {time_mods[time_of_day]}"

        st.divider()
        cloth_main = st.selectbox("衣装カテゴリー", list(CATEGORIES.keys()))
        cloth_detail = st.text_input("衣装仕様", placeholder="例：黒サテン")
        hair_s = st.selectbox("💇 髪型", list(HAIR_STYLES.keys()))
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()))
        
        run_btn = st.button("✨ 4枚一括生成", type="primary")

    # --- 生成ロジック ---
    if run_btn and st.session_state.source_bytes:
        st.session_state.generated_images = [None] * 4
        
        # ポーズ抽選 (重複なし)
        if pose_pattern == "立ち3:座り1":
            selected_stands = random.sample(STAND_POOL, 3)
            selected_sits = random.sample(SIT_POOL, 1)
        else:
            selected_stands = random.sample(STAND_POOL, 2)
            selected_sits = random.sample(SIT_POOL, 2)
        
        final_pool = selected_stands + selected_sits
        random.shuffle(final_pool)
        st.session_state.current_poses = [f"{p}, {pose_plus}" for p in final_pool]

        status = st.empty(); progress = st.progress(0)
        
        # 1. アンカー抽出
        status.info("🕒 Step 1/2: 衣装アンカー作成中...")
        ref_part = types.Part.from_bytes(data=st.session_state.ref_bytes, mime_type='image/jpeg') if st.session_state.ref_bytes else None
        id_part = types.Part.from_bytes(data=st.session_state.source_bytes, mime_type='image/jpeg')
        
        anchor_data = generate_image_by_text(client, "Flat lay clothing shot", id_part, ref_part, f"Professional catalog flat lay of {cloth_detail}", "Studio lighting", "original", "original", cloth_main)
        st.session_state.anchor_part = types.Part.from_bytes(data=anchor_data, mime_type='image/png')
        st.session_state.wardrobe_task = f"Strictly apply design from IMAGE 2. {cloth_detail}."
        
        # 2. 4枚生成
        for i in range(4):
            status.info(f"🎨 Step 2/2: 生成中 ({i+1}/4)...")
            res = generate_image_by_text(client, st.session_state.current_poses[i], id_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
            if isinstance(res, bytes):
                st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
            progress.progress((i+1)/4)
        
        status.empty(); st.rerun()

    # --- 表示エリア ---
    if any(img is not None for img in st.session_state.generated_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                img = st.session_state.generated_images[i]
                if img:
                    st.image(img, use_container_width=True)
                    c1, c2 = st.columns(2)
                    with c1:
                        # 保存ボタン
                        buf = io.BytesIO(); img.save(buf, format="JPEG")
                        st.download_button("💾 保存", buf.getvalue(), f"v3_img_{i+1}.jpg", "image/jpeg", key=f"dl_{i}")
                    with c2:
                        # 撮り直しボタン
                        if st.button("🔄 撮り直し", key=f"re_{i}"):
                            if st.session_state.source_bytes:
                                with st.spinner("再生成中..."):
                                    id_p = types.Part.from_bytes(data=st.session_state.source_bytes, mime_type='image/jpeg')
                                    res = generate_image_by_text(client, st.session_state.current_poses[i], id_p, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
                                    if isinstance(res, bytes):
                                        st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
                                        st.rerun()
                            else:
                                st.error("Source image missing.")
