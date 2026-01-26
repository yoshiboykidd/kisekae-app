import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 定義データ (v3.1: 日本人女性・黄金律・直立なし) ---
HAIR_STYLES = {"元画像のまま": "original hairstyle from IMAGE 1", "ゆるふあ巻き": "soft loose wavy curls", "ハーフアップ": "elegant half-up style", "ツインテール": "playful twin tails", "ポニーテール": "neat ponytail", "まとめ髪": "sophisticated updo bun", "ストレート": "sleek long straight hair"}
HAIR_COLORS = {"元画像のまま": "original hair color from IMAGE 1", "ナチュラルブラック": "natural black hair", "ダークブラウン": "deep dark brown hair", "ashベージュ": "ash beige hair color", "ミルクティーグレージュ": "soft milk-tea greige hair color", "ピンクブラウン": "pinkish brown hair color", "ハニーブロンド": "bright honey blonde hair color"}

STAND_PROMPTS = ["Full body, leaning against a wall", "Full body, walking slowly", "Full body, weight on one leg", "Full body, looking over shoulder, slight body turn", "Full body, gently adjusting hair with one hand", "Full body, 3/4 view, elegant posture", "Full body, hands clasped gently in front"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways on chair", "Full body, sitting on steps", "Full body, sitting with legs crossed elegantly", "Full body, leaning slightly forward on a chair", "Full body, sitting and looking away slightly", "Full body, sitting on a high stool, one leg down"]

CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual fashion", "back_prompt": "natural soft skin"},
    "2. 水着（リゾート）": {"en": "Resort fashion", "back_prompt": "healthy skin glow"},
    "3. 部屋着（リラックス）": {"en": "Lounge silk-fashion", "back_prompt": "ultra-soft focus"}, 
    "4. オフィス（スーツ）": {"en": "Business professional", "back_prompt": "sharp lighting"},
    "5. 夜の装い（ドレス）": {"en": "Luxury evening fashion", "back_prompt": "luxury bokeh, dramatic lighting"}
}

# --- 2. 生成エンジン (ABSOLUTE FACIAL & BODY LOCK) ---
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
            # Pydanticエラーを回避するための安全なデータ取得
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content.parts:
                    return candidate.content.parts[0].inline_data.data
                
                # エラーメッセージの翻訳・可視化
                reason = getattr(candidate, 'finish_reason', 'UNKNOWN')
                if reason in ['SAFETY', 'IMAGE_OTHER', 'PROHIBITED_CONTENT']:
                    return f"検閲ブロック ({reason}): 衣装や単語がAIの制限に触れました。表現をマイルドにしてください。"
            
            return "AI_REJECTED: 画像が生成されませんでした。"
            
        except Exception as e:
            # Pydanticの列挙型エラー(IMAGE_OTHER)をここでキャッチしてユーザーに通知
            if "validation error" in str(e).lower() or "IMAGE_OTHER" in str(e):
                return "検閲ブロック (SYSTEM_FILTER): AIが画像を拒絶しました。別の衣装詳細を試してください。"
            if "503" in str(e) and attempt < max_retries:
                time.sleep(2); continue
            return f"SYSTEM_ERROR: {str(e)}"
    return "FAILED"

def generate_image_by_text(client, pose_text, id_part, anchor_part, wardrobe_task, bg_prompt, hair_s, hair_c, cat_key):
    cat_info = CATEGORIES[cat_key]
    item_control = "DO NOT add any bags. Keep hands empty unless specified."
    prompt = (
        f"CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK.\n"
        f"1. FACE FIDELITY (IMAGE 1): Replicate EXACT face from IMAGE 1. 100% identity match.\n"
        f"2. HAIR: Style: {hair_s}, Color: {hair_c}.\n"
        f"3. PHYSICAL: ABSOLUTE BODY VOLUME LOCK. Match IMAGE 1 volume exactly.\n"
        f"4. POSE: {pose_text}. {item_control}\n"
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

    # 反映確認用の新バージョン表記
    st.header("✨ AI KISEKAE ツール ver3.13")

    with st.sidebar:
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="k_src")
        if src_img:
            st.session_state.source_bytes = src_img.getvalue()
            st.image(src_img, use_container_width=True)
        
        st.divider()
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="k_ref")
        if ref_img:
            st.session_state.ref_bytes = ref_img.getvalue()
            st.image(ref_img, use_container_width=True)

        st.divider()
        cloth_main = st.selectbox("カテゴリー", list(CATEGORIES.keys()))
        # アドバイス：ここには「バニー」と書かず、素材や形状（サテン、ボディスーツ等）のみを書く
        cloth_detail = st.text_input("衣装詳細 (例: black satin bodysuit, bow tie)", placeholder="単語選びが重要です")

        st.divider()
        hair_s = st.selectbox("💇 髪型", list(HAIR_STYLES.keys()))
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()))

        st.divider()
        st.subheader("📍 ロケーション")
        bg_text = st.text_input("場所を入力", value="", placeholder="街角のオープンカフェ")
        time_of_day = st.radio("時間帯", ["昼 (Daylight)", "夕方 (Golden Hour)", "夜 (Night)"])
        st.divider()
        pose_pattern = st.radio("生成比率", ["立ち3:座り1", "立ち2:座り2"])
        run_btn = st.button("✨ 4枚一括生成", type="primary")

    if run_btn and st.session_state.source_bytes:
        time_mods = {"昼 (Daylight)": "bright daylight", "夕方 (Golden Hour)": "golden sunset", "夜 (Night)": "night lights"}
        st.session_state.final_bg = f"{bg_text}, {time_mods[time_of_day]}, portrait bokeh"
        
        if pose_pattern == "立ち3:座り1":
            st.session_state.current_poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
        else:
            st.session_state.current_poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
        random.shuffle(st.session_state.current_poses)

        status = st.empty(); progress = st.progress(0)
        
        # --- Step 1: アンカー作成 (擬態プロンプトをさらに強化) ---
        status.info("🕒 Step 1/2: 衣装デザイン抽出中...")
        ref_content = [types.Part.from_bytes(data=st.session_state.ref_bytes, mime_type='image/jpeg')]
        # 「バニー」を一切排除し、「プロのステージ衣装（ボディスーツ）」としてAIに認識させる
        anchor_prompt = f"Professional apparel photography of a high-quality satin one-piece stage bodysuit. {cloth_detail}. Neutral studio lighting, catalog style. NO forbidden elements."
        res_data = generate_with_retry(client, ref_content, anchor_prompt)
        
        if isinstance(res_data, bytes):
            st.session_state.anchor_part = types.Part.from_bytes(data=res_data, mime_type='image/png')
            st.session_state.wardrobe_task = f"Strictly apply the design from the clothing anchor. {cloth_detail}."
            
            # --- Step 2: メイン生成 ---
            id_part = types.Part.from_bytes(data=st.session_state.source_bytes, mime_type='image/jpeg')
            for i in range(4):
                status.info(f"🎨 Step 2/2: 生成中 ({i+1}/4)...")
                res = generate_image_by_text(client, st.session_state.current_poses[i], id_part, st.session_state.anchor_part, st.session_state.wardrobe_task, st.session_state.final_bg, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], cloth_main)
                if isinstance(res, bytes):
                    st.session_state.generated_images[i] = Image.open(io.BytesIO(res)).resize((600, 900))
                else:
                    st.error(f"枠 {i+1}: {res}")
                progress.progress((i+1)/4)
            status.empty(); st.rerun()
        else:
            status.error(f"🚫 失敗: {res_data}")
