import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- [定義データは v2.91 と同じため省略] ---
# HAIR_STYLES, HAIR_COLORS, STAND_PROMPTS, SIT_PROMPTS, CATEGORIES はそのまま

# --- [生成エンジンも v2.91 の「ねじ伏せ型」を維持] ---
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
            return "SAFETY_BLOCK"
        except Exception as e:
            if "503" in str(e) and attempt < max_retries:
                time.sleep(2); continue
            return str(e)
    return "FAILED"

def generate_image_by_text(client, pose_text, identity_part, anchor_part, wardrobe_task, bg_prompt, hair_style_en, hair_color_en, cat_key):
    cat_info = CATEGORIES[cat_key]
    prompt = (
        f"CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK.\n"
        f"1. FACE FIDELITY (IMAGE 1): Replicate EXACT face from IMAGE 1. 100% identity match.\n"
        f"2. HAIR: Style: {hair_style_en}, Color: {hair_color_en}.\n"
        f"3. PHYSICAL: ABSOLUTE BODY VOLUME LOCK. Match IMAGE 1.\n"
        f"4. POSE: {pose_text}. 85mm portrait. 2:3 aspect ratio.\n"
        f"5. WARDROBE: {wardrobe_task}\n"
        f"6. RENDER: {bg_prompt}, {cat_info['back_prompt']}, soft facial fill-light, 8k, neutral expression."
    )
    return generate_with_retry(client, [identity_part, anchor_part], prompt)

# --- [UI メイン処理: サムネイル表示を追加] ---
def show_kisekae_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    if "generated_images" not in st.session_state:
        st.session_state.generated_images = [None] * 4
    if "current_pose_texts" not in st.session_state:
        st.session_state.current_pose_texts = [None] * 4

    st.header("✨ AI KISEKAE Main System (v2.92)")
    
    with st.sidebar:
        # --- IMAGE 1 (キャスト) ---
        source_img = st.file_uploader("キャスト写真 (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="k_src")
        if source_img:
            # アップロードされたらすぐにサムネイルを表示
            st.image(source_img, caption="IMAGE 1: キャスト確認", use_container_width=True)
        
        st.divider()

        # --- IMAGE 2 (衣装) ---
        ref_img = st.file_uploader("衣装参考 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="k_ref")
        if ref_img:
            # アップロードされたらすぐにサムネイルを表示
            st.image(ref_img, caption="IMAGE 2: 衣装参考確認", use_container_width=True)

        st.divider()
        
        # 設定項目
        cloth_main = st.selectbox("衣装カテゴリー", list(CATEGORIES.keys()))
        cloth_detail = st.text_input("衣装仕様書", placeholder="例：黒サテンの光沢")
        hair_s = st.selectbox("💇 髪型アレンジ", list(HAIR_STYLES.keys()))
        hair_c = st.selectbox("🎨 髪色変更", list(HAIR_COLORS.keys()))
        st.divider()
        bg_text = st.text_input("場所", "高級ホテル")
        time_of_day = st.radio("時間帯", ["昼 (Daylight)", "夕方 (Golden Hour)", "夜 (Night)"])
        pose_pattern = st.radio("生成配分", ["立ち3:座り1", "立ち2:座り2"])
        run_btn = st.button("✨ 4枚一括生成", type="primary")

    # --- [生成処理ロジックは v2.91 と同じため省略] ---
    if run_btn and source_img:
        # (中略: アンカー生成 -> 4枚一括生成のループ)
        # ※ v2.91 のコードをそのままここに配置してください
        st.session_state.generated_images = [None] * 4
        time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "golden sunset", "夜 (Night)": "night lights"}
        st.session_state.final_bg_prompt = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh"
        
        if pose_pattern == "立ち3:座り1":
            poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
        else:
            poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
        random.shuffle(poses)
        st.session_state.current_pose_texts = poses

        status = st.empty(); progress = st.progress(0)
        status.info("🕒 Step 1/2: 衣装アンカー抽出中...")
        anchor_prompt = f"Professional product shot of {CATEGORIES[cloth_main]['en']}. {cloth_detail}. 1:1 aspect ratio."
        contents = [types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')] if ref_img else []
        res_data = generate_with_retry(client, contents, anchor_prompt)
        
        if isinstance(res_data, bytes):
            st.session_state.anchor_part = types.Part.from_bytes(data=res_data, mime_type='image/png')
            st.session_state.wardrobe_task = f"Strictly apply design from IMAGE 2. {cloth_detail}."
            identity_part = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')
            for i in range(4):
                status.info(f"🎨 Step 2/2: 生成中 ({i+1}/4)...")
                res = generate_image_by_text(client, st.session_state.current_pose_texts[i], identity_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
                if isinstance(res, bytes):
                    st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
                progress.progress((i+1)/4)
            status.empty(); st.rerun()
        else:
            st.error(f"アンカー失敗: {res_data}")

    # --- [表示エリアも v2.91 を維持] ---
    if any(img is not None for img in st.session_state.generated_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                img = st.session_state.generated_images[i]
                if img:
                    st.image(img, use_container_width=True)
                    c1, c2 = st.columns(2)
                    with c1:
                        buf = io.BytesIO(); img.save(buf, format="JPEG")
                        st.download_button("💾 保存", buf.getvalue(), f"img_{i+1}.jpg", "image/jpeg", key=f"dl_{i}")
                    with c2:
                        if st.button("🔄 撮り直し", key=f"re_{i}"):
                            with st.spinner("再生成中..."):
                                id_p = types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')
                                res = generate_image_by_text(client, st.session_state.current_pose_texts[i], id_p, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg_prompt, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
                                if isinstance(res, bytes):
                                    st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
                                    st.rerun()
