import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os
from PIL import Image

# --- 1. 定義データ (通常版より完全移植) [cite: 2026-01-16] ---
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
    "ashベージュ": "ash beige hair color",
    "ミルクティーグレージュ": "soft milk-tea greige hair color",
    "ピンクブラウン": "pinkish brown hair color",
    "ハニーブロンド": "bright honey blonde hair color"
}

STAND_PROMPTS = [
    "Full body, leaning against a wall", "Full body, walking slowly", 
    "Full body, weight on one leg", "Full body, looking over shoulder, slight body turn", 
    "Full body, gently adjusting hair with one hand", "Full body, 3/4 view, elegant posture"
]
SIT_PROMPTS = [
    "Full body, sitting on sofa", "Full body, sitting sideways on chair", 
    "Full body, sitting with legs crossed elegantly", "Full body, leaning slightly forward on a chair", 
    "Full body, sitting on a high stool, one leg down"
]

# --- 2. DX専用プロンプト構築エンジン (黄金律の強制適用) [cite: 2026-01-16] ---
def get_final_dx_prompt(pose, anchor_text, hair_s, hair_c, id_weight):
    """顔・体型・衣装・質感を統合した最終プロンプトを作成"""
    identity_lock = (
        "CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK [cite: 2026-01-16]. "
        "STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK [cite: 2026-01-16]. "
        "Match EXACT face and body mass of IMAGE 1. 100% identity match [cite: 2026-01-16]. "
        "Do not beautify or thin the body [cite: 2026-01-16]. "
    )
    render_recipe = (
        "Subject is a Japanese woman [cite: 2025-12-30]. "
        "Hyper-realistic photography, shot on Sony A7R IV, 35mm lens, f/2.8, "
        "highly detailed natural skin texture with visible pores, "
        "soft facial fill-light, cinematic lighting, 8k photo, film grain [cite: 2026-01-16]."
    )
    # アンカーテキストをWARDROBEに封じ込める
    return f"{identity_lock} POSE: {pose}. HAIR: {hair_s}, Color: {hair_c}. WARDROBE: {anchor_text}. {render_recipe}"

def call_fal_api(face_url, prompt, id_weight, g_scale, steps):
    """Fal.ai Flux-PuLID APIの実行 [cite: 2026-03-01]"""
    return fal_client.subscribe(
        "fal-ai/flux-pulid",
        arguments={
            "prompt": prompt,
            "reference_image_url": face_url,
            "id_weight": id_weight,
            "num_inference_steps": steps,
            "guidance_scale": g_scale,
            "enable_safety_checker": False, # 検閲オフ [cite: 2026-03-01]
            "image_size": "portrait_4_3"
        }
    )

# --- 3. UI メイン処理 ---
def show_dx_ui():
    # APIキーと環境変数の準備
    if "GEMINI_API_KEY" not in st.secrets or "FAL_KEY" not in st.secrets:
        st.error("🔑 APIキー(GEMINI_API_KEY または FAL_KEY)が設定されていません。")
        st.stop()
    
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    # セッション状態の初期化
    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_anchor" not in st.session_state: st.session_state.dx_anchor = ""

    st.header("💎 AI KISEKAE DX v3.18 (Hybrid Anchor)")
    st.caption("【DX仕様】Geminiで衣装を解析し、Fal.aiで検閲なし描画を行います [cite: 2026-01-16, 2026-03-01]")

    with st.sidebar:
        st.subheader("🖼️ ソース入力")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_src")
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_ref")
        
        st.divider()
        st.subheader("💇 スタイル設定")
        hair_s = st.selectbox("髪型", list(HAIR_STYLES.keys()), key="dx_h_s")
        hair_c = st.selectbox("髪色", list(HAIR_COLORS.keys()), key="dx_h_c")
        cloth_note = st.text_input("衣装の補足指示", placeholder="例: black satin, lace trim")
        
        st.divider()
        st.subheader("⚙️ 生成パラメータ")
        id_weight = st.slider("顔の固定強度 (ID Weight)", 0.0, 1.0, 0.82)
        g_scale = st.slider("命令遵守度 (Guidance Scale)", 1.0, 10.0, 3.5, help="3.5前後が実写感と指示の両立に最適です。")
        steps = st.slider("描き込み回数 (Steps)", 20, 50, 30)
        
        st.divider()
        pose_pattern = st.radio("比率", ["立ち3:座り1", "立ち2:座り2"], key="dx_p_p")
        run_btn = st.button("🚀 DX 4枚一括生成", type="primary")

    # --- 生成メインロジック ---
    if run_btn and src_img and ref_img:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            # Step 1: Geminiによる衣装アンカーの作成 [cite: 2026-01-16]
            status.info("🕒 Step 1/2: 衣装のデザインを解析して固定しています...")
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            analysis_p = f"Analyze this clothing in detail. Describe material, color, and specific design elements for AI image generation. {cloth_note}"
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, analysis_p])
            st.session_state.dx_anchor = response.text
            
            # Step 2: Fal.aiによる画像生成
            status.info("⏳ キャストデータを転送中...")
            face_url = fal_client.upload(src_img.getvalue(), "image/jpeg")
            
            # ポーズの抽選
            if pose_pattern == "立ち3:座り1":
                poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
            else:
                poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
            random.shuffle(poses)
            st.session_state.dx_current_poses = poses

            for i in range(4):
                status.info(f"🎨 DX描画中 ({i+1}/4)...")
                final_p = get_final_dx_prompt(poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], id_weight)
                
                try:
                    result = call_fal_api(face_url, final_p, id_weight, g_scale, steps)
                    image_url = result['images'][0]['url']
                    st.session_state.dx_images[i] = Image.open(requests.get(image_url, stream=True).raw)
                except Exception as inner_e:
                    st.warning(f"⚠️ 枠 {i+1} で中断されました。")
                    st.sidebar.error(f"枠 {i+1} エラー: {str(inner_e)}")
                    break
                progress.progress((i+1)/4)
            status.empty()
        except Exception as e:
            st.error(f"🚫 システムエラー: {str(e)}")

    # --- 表示エリア ---
    if any(img is not None for img in st.session_state.dx_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                img = st.session_state.dx_images[i]
                if img:
                    st.image(img, use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"dx_{i}.jpg", "image/jpeg", key=f"dl_dx_{i}")
                    
                    if st.button("🔄 撮り直し", key=f"re_dx_{i}"):
                        with st.spinner("DX再生成中..."):
                            try:
                                face_u = fal_client.upload(src_img.getvalue(), "image/jpeg")
                                pr = get_final_dx_prompt(st.session_state.dx_current_poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c], id_weight)
                                res = call_fal_api(face_u, pr, id_weight, g_scale, steps)
                                st.session_state.dx_images[i] = Image.open(requests.get(res['images'][0]['url'], stream=True).raw)
                                st.rerun()
                            except Exception as e: st.error(f"再生成失敗: {str(e)}")
