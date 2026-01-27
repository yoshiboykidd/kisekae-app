import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 定義データ (v2.94 魂の継承) ---
HAIR_STYLES = {"元画像のまま": "original hairstyle from IMAGE 1", "ゆるふあ巻き": "soft loose wavy curls", "ハーフアップ": "elegant half-up style", "ツインテール": "playful twin tails", "ポニーテール": "neat ponytail", "まとめ髪": "sophisticated updo bun", "ストレート": "sleek long straight hair"}
HAIR_COLORS = {"元画像のまま": "original hair color from IMAGE 1", "ナチュラルブラック": "natural black hair", "ダークブラウン": "deep dark brown hair", "ashベージュ": "ash beige hair color", "ミルクティーグレージュ": "soft milk-tea greige hair color", "ピンクブラウン": "pinkish brown hair color", "ハニーブロンド": "bright honey blonde hair color"}

STAND_PROMPTS = ["Full body, leaning against a wall", "Full body, walking slowly", "Full body, weight on one leg", "Full body, looking over shoulder, slight body turn", "Full body, gently adjusting hair with one hand", "Full body, 3/4 view, elegant posture", "Full body, hands clasped gently in front"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways on chair", "Full body, sitting on steps", "Full body, sitting with legs crossed elegantly", "Full body, leaning slightly forward on a chair", "Full body, sitting and looking away slightly", "Full body, sitting on a high stool, one leg down"]

CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual everyday Japanese fashion", "back_prompt": "natural soft skin"},
    "2. 水着（リゾート）": {"en": "High-end stylish resort swimwear", "back_prompt": "healthy skin glow"},
    "3. 部屋着（リラックス）": {"en": "Elegant silk night-fashion, satin slip", "back_prompt": "ultra-soft focus"}, 
    "4. オフィス（スーツ）": {"en": "Elegant business professional attire", "back_prompt": "sharp corporate lighting"},
    "5. 夜の装い（ドレス）": {"en": "Sophisticated evening gown", "back_prompt": "luxury bokeh, dramatic lighting"}
}

LOCATION_EXAMPLES = "・街角 of Open Cafe\n・洗練された並木道\n・お洒落なセレクトショップ\n・ルーフトップテラス\n・都会を一望するバーカウンター\n・住宅街の静かな公園\n・地元の小さな商店街"

# --- 2. 生成エンジン ---
def generate_with_retry(client, contents, prompt, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model='gemini-3-pro-image-preview',
                contents=contents + [prompt],
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE'],
                    safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')]
                )
            )
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content.parts:
                    return candidate.content.parts[0].inline_data.data
                reason = getattr(candidate, 'finish_reason', 'UNKNOWN')
                return f"検閲ブロック ({reason})"
            return "AI_REJECTED"
        except Exception as e:
            if "503" in str(e) and attempt < max_retries:
                time.sleep(2); continue
            if "validation error" in str(e).lower() or "IMAGE_OTHER" in str(e):
                return "検閲ブロック (SYSTEM_FILTER)"
            return f"SYSTEM_ERROR: {str(e)}"
    return "FAILED"

def generate_image_by_text(client, pose_text, id_part, anchor_part, wardrobe_task, bg_prompt, hair_s, hair_c, cat_key):
    cat_info = CATEGORIES[cat_key]
    prompt = (
        f"CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK.\n"
        f"1. FACE FIDELITY (IMAGE 1): Replicate EXACT face from IMAGE 1. 100% identity match.\n"
        f"2. HAIR: Style: {hair_s}, Color: {hair_c}.\n"
        f"3. PHYSICAL: ABSOLUTE BODY VOLUME LOCK. Match IMAGE 1 volume exactly.\n"
        f"4. POSE: {pose_text}. 85mm portrait. 2:3 aspect ratio. DO NOT add any bags.\n"
        f"5. WARDROBE: {wardrobe_task}\n"
        f"6. RENDER: {bg_prompt}, {cat_info['back_prompt']}, soft facial fill-light, 8k, neutral expression."
    )
    return generate_with_retry(client, [id_part, anchor_part], prompt)

# --- 3. UI メイン処理 ---
def show_kisekae_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    if "generated_images" not in st.session_state: st.session_state.generated_images = [None] * 4
    if "source_bytes" not in st.session_state: st.session_state.source_bytes = None
    if "ref_bytes" not in st.session_state: st.session_state.ref_bytes = None

    st.header("✨ AI KISEKAE ツール ver 3.17 (成果表示版)")

    with st.sidebar:
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="k_src")
        if src_img: st.session_state.source_bytes = src_img.getvalue(); st.image(src_img, use_container_width=True)
        st.divider()
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="k_ref")
        if ref_img: st.session_state.ref_bytes = ref_img.getvalue(); st.image(ref_img, use_container_width=True)
        st.divider()
        cloth_main = st.selectbox("カテゴリー", list(CATEGORIES.keys()))
        cloth_detail = st.text_input("衣装詳細", placeholder="例: black satin")
        hair_s = st.selectbox("💇 髪型", list(HAIR_STYLES.keys()))
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()))
        st.divider()
        bg_text = st.text_input("場所", value="", placeholder="街角のオープンカフェ")
        time_of_day = st.radio("時間帯", ["昼", "夕方", "夜"])
        st.caption("【コピー用例文】")
        st.text(LOCATION_EXAMPLES)
        st.divider()
        pose_pattern = st.radio("比率", ["立ち3:座り1", "立ち2:座り2"])
        run_btn = st.button("✨ 4枚一括生成", type="primary")

    if run_btn and st.session_state.source_bytes:
        st.session_state.generated_images = [None] * 4
        time_mods = {"昼": "bright daylight", "夕方": "golden sunset", "夜": "night lights"}
        st.session_state.final_bg = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh"
        
        if pose_pattern == "立ち3:座り1":
            st.session_state.current_poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
        else:
            st.session_state.current_poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
        random.shuffle(st.session_state.current_poses)

        status = st.empty(); progress = st.progress(0)
        
        # --- Step 1 ---
        status.info("🕒 Step 1/2: デザイン抽出中...")
        ref_content = [types.Part.from_bytes(data=st.session_state.ref_bytes, mime_type='image/jpeg')]
        anchor_prompt = f"Professional clothing photography. {cloth_detail}. Neutral background."
        res_data = generate_with_retry(client, ref_content, anchor_prompt)
        
        if not isinstance(res_data, bytes):
            status.error(f"🚫 Step 1 で検閲されました: {res_data}")
            st.stop()
        
        st.session_state.anchor_part = types.Part.from_bytes(data=res_data, mime_type='image/png')
        st.session_state.wardrobe_task = f"Strictly apply the design from the clothing anchor. {cloth_detail}."
        
        # --- Step 2 ---
        id_part = types.Part.from_bytes(data=st.session_state.source_bytes, mime_type='image/jpeg')
        for i in range(4):
            status.info(f"🎨 Step 2/2: 生成中 ({i+1}/4)...")
            res = generate_image_by_text(client, st.session_state.current_poses[i], id_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
            
            if isinstance(res, bytes):
                st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
            else:
                # ここで止めるのではなく「中断」してループを抜ける
                st.warning(f"⚠️ 枠 {i+1} 以降はブロックされました。成功分のみ表示します。")
                st.sidebar.error(f"ブロック理由: {res}")
                break # ループを抜ける
            progress.progress((i+1)/4)
        
        status.empty()
        # st.stop() を呼ばず、そのままコード末尾の表示エリアまで流す

    # --- 表示エリア (ループの外側にあるので st.stop しなければ必ず実行される) ---
    if any(img is not None for img in st.session_state.generated_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                img = st.session_state.generated_images[i]
                if img:
                    st.image(img, use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"img_{i}.jpg", "image/jpeg", key=f"dl_{i}")
                    if st.button("🔄 撮り直し", key=f"re_{i}"):
                        with st.spinner("再生成中..."):
                            id_p = types.Part.from_bytes(data=st.session_state.source_bytes, mime_type='image/jpeg')
                            res = generate_image_by_text(client, st.session_state.current_poses[i], id_p, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
                            if isinstance(res, bytes):
                                st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
                                st.rerun()
