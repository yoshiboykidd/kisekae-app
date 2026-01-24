import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 定義データ (v3.0 黄金律準拠) ---
HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft loose wavy curls", "ハーフアップ": "half-up style", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo bun", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "original color", "ナチュラルブラック": "natural black", "ダークブラウン": "deep dark brown", "ashベージュ": "ash beige", "ミルクティーグレージュ": "milk-tea greige", "ピンクブラウン": "pinkish brown"}

STAND_PROMPTS = ["Full body, standing naturally", "Full body, leaning against a wall", "Full body, walking slowly", "Full body, weight on one leg"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways on chair", "Full body, sitting on steps"]

CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual fashion", "back": "natural soft skin"},
    "2. 水着（リゾート）": {"en": "Resort swimwear", "back": "healthy skin glow"},
    "3. 部屋着（リラックス）": {"en": "Silk night-fashion", "back": "ultra-soft focus"},
    "4. オフィス（スーツ）": {"en": "Business attire", "back": "sharp lighting"},
    "5. 夜の装い（ドレス）": {"en": "Evening gown", "back": "luxury bokeh"}
}

LOCATION_EXAMPLES = "・街角のオープンカフェ\n・洗練された並木道\n・お洒落なセレクトショップ\n・ルーフトップテラス\n・都会を一望するバーカウンター\n・住宅街の静かな公園\n・地元の小さな商店街"

# --- 生成エンジン (v3.0 顔・体型固定 & カバン禁止) ---
def generate_image_by_text(client, pose_text, id_part, anchor_part, wardrobe_task, bg_prompt, hair_s, hair_c, cat_key):
    cat_info = CATEGORIES[cat_key]
    # 【v3.0 鉄則】手ぶら強制。指定がない限りバッグ類を排除
    item_control = "DO NOT add any bags. Keep hands empty unless a specific item is mentioned."
    
    prompt = (
        f"CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK. Face match 1:1 with IMAGE 1.\n"
        f"2. HAIR: Style: {hair_s}, Color: {hair_c}.\n"
        f"3. PHYSICAL: ABSOLUTE BODY VOLUME LOCK. Match IMAGE 1 body volume exactly.\n"
        f"4. POSE: {pose_text}. {item_control}\n"
        f"5. WARDROBE: {wardrobe_task}\n"
        f"6. RENDER: {bg_prompt}, {cat_info['back']}, soft facial fill-light, 8k, neutral expression."
    )
    
    try:
        res = client.models.generate_content(
            model='gemini-3-pro-image-preview',
            contents=[id_part, anchor_part, prompt],
            config=types.GenerateContentConfig(
                response_modalities=['IMAGE'],
                safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')]
            )
        )
        return res.candidates[0].content.parts[0].inline_data.data
    except: return None

# --- ✨ AI KISEKAE UI 表示部 ---
def show_kisekae_ui():
    st.header("✨ AI KISEKAE ツール ver3.0")
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    if "generated_images" not in st.session_state: st.session_state.generated_images = [None] * 4
    if "source_bytes" not in st.session_state: st.session_state.source_bytes = None
    if "ref_bytes" not in st.session_state: st.session_state.ref_bytes = None

    with st.sidebar:
        # 親ファイル(app.py)のメニュー直下から表示が始まる
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'])
        if src_img: st.session_state.source_bytes = src_img.getvalue(); st.image(src_img)
        
        st.divider()
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'])
        if ref_img: st.session_state.ref_bytes = ref_img.getvalue(); st.image(ref_img)

        st.divider()
        cloth_main = st.selectbox("カテゴリー", list(CATEGORIES.keys()))
        cloth_detail = st.text_input("衣装詳細", placeholder="例：黒サテン、グラスを持つ")

        st.divider()
        hair_s = st.selectbox("💇 髪型", list(HAIR_STYLES.keys()))
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()))

        st.divider()
        st.subheader("📍 ロケーション")
        bg_text = st.text_input("場所を入力", value="", placeholder="街角のオープンカフェ")
        time_of_day = st.radio("時間帯", ["昼 (Daylight)", "夕方 (Golden Hour)", "夜 (Night)"])
        st.caption("【コピー用例文】")
        st.text(LOCATION_EXAMPLES)

        st.divider()
        pose_pattern = st.radio("生成比率", ["立ち3:座り1", "立ち2:座り2"])
        run_btn = st.button("✨ 4枚一括生成", type="primary")

    if run_btn and st.session_state.source_bytes:
        # 生成ロジック開始...
        time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "golden sunset", "夜 (Night)": "night lights"}
        final_bg = f"{bg_text}, {time_mods[time_of_day]}"
        
        if pose_pattern == "立ち3:座り1": poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
        else: poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
        random.shuffle(poses)

        id_part = types.Part.from_bytes(data=st.session_state.source_bytes, mime_type='image/jpeg')
        ref_part = types.Part.from_bytes(data=st.session_state.ref_bytes, mime_type='image/jpeg') if st.session_state.ref_bytes else id_part
        
        status = st.empty(); progress = st.progress(0)
        status.info("🕒 衣装アンカー作成中...")
        # 下着等の直接表現を避けアパレル用語のみを使用
        anchor_data = generate_image_by_text(client, "Flat lay", id_part, ref_part, f"Catalog: {cloth_detail}", "Studio", "original", "original", cloth_main)
        
        if anchor_data:
            anchor_part = types.Part.from_bytes(data=anchor_data, mime_type='image/png')
            for i in range(4):
                status.info(f"🎨 生成中 ({i+1}/4)...")
                res = generate_image_by_text(client, poses[i], id_part, anchor_part, cloth_detail, final_bg, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
                if res: st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
                progress.progress((i+1)/4)
            status.empty(); st.rerun()

    # 画像表示
    if any(img is not None for img in st.session_state.generated_images):
        cols = st.columns(2)
        for i, img in enumerate(st.session_state.generated_images):
            if img:
                with cols[i%2]:
                    st.image(img, use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"img_{i}.jpg", "image/jpeg", key=f"dl_{i}")
