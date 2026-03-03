import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os, time
from PIL import Image

# --- 1. 定義データ (ポーズ・スタイル：通常版完全互換) [cite: 2026-01-16] ---
HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft wavy curls", "ハーフアップ": "half-up", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "original color", "ナチュラルブラック": "black", "ダークブラウン": "dark brown", "ashベージュ": "ash beige", "ミルクティーグレージュ": "greige", "ピンクブラウン": "pink brown", "ハニーブロンド": "honey blonde"}
STAND_PROMPTS = ["Full body, leaning against a wall", "Full body, walking", "Full body, weight on one leg", "Full body, 3/4 view, elegant posture"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways on chair", "Full body, sitting on steps", "Full body, legs crossed"]

# --- 2. 黄金律 v2.66：鉄壁のプロンプトエンジン [cite: 2026-01-16] ---
def get_final_dx_prompt(pose, anchor_text, hair_s, hair_c):
    """
    衣装の無視と裸化を物理的に防ぎ、体型を死守する [cite: 2026-01-16]
    """
    # 1. 衣装を最優先（AIの脱がせたい衝動を抑え込む）
    # lingerie等の単語をNight-fashionに変換し、透けない素材を強制 [cite: 2026-01-16]
    safe_anchor = anchor_text.replace("lingerie", "Night-fashion").replace("nude", "clothed")
    wardrobe_priority = (
        f"WARDROBE: {safe_anchor}, solid non-transparent fabric, opaque material, "
        "high-quality garment construction, realistic clothing folds. "
    )
    
    # 2. 体型と顔の固定（黄金律 ver 2.66） [cite: 2026-01-16]
    identity_lock = (
        "STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK [cite: 2026-01-16]. "
        "CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK [cite: 2026-01-16]. "
        "Match the EXACT body mass, shoulder width, and natural curves of IMAGE 1. "
        "1:1 physical volume match. No beautification, no thinning. "
        "Maintain the original fleshy silhouette and realistic build [cite: 2026-01-16]. "
    )
    
    # 3. 画質と質感
    render = (
        "Subject: Japanese woman [cite: 2025-12-30]. "
        "Hyper-realistic raw photography, Sony A7R IV, 35mm lens, f/2.8, "
        "detailed skin texture with visible pores, cinematic lighting, 8k photo, film grain [cite: 2026-01-16]."
    )
    
    return f"{wardrobe_priority} {identity_lock} POSE: {pose}. HAIR: {hair_s}, Color: {hair_c}. {render}"

def generate_with_retry(face_url, prompt, id_weight, g_scale, steps, max_retries=2):
    """黄金律：503エラーリトライ機能 [cite: 2026-01-16]"""
    for attempt in range(max_retries + 1):
        try:
            return fal_client.subscribe(
                "fal-ai/flux-pulid",
                arguments={
                    "prompt": prompt, "reference_image_url": face_url,
                    "id_weight": id_weight, "guidance_scale": g_scale,
                    "num_inference_steps": steps, "enable_safety_checker": False
                }
            )
        except Exception as e:
            if "503" in str(e) and attempt < max_retries:
                time.sleep(2); continue
            raise e

# --- 3. UI メイン処理 ---
def show_dx_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_src_bytes" not in st.session_state: st.session_state.dx_src_bytes = None
    if "dx_anchor" not in st.session_state: st.session_state.dx_anchor = ""

    st.header("💎 AI KISEKAE DX v3.29 (Final)")
    st.caption("【DX仕様】衣装優先・体型死守・黄金律 v2.66 準拠 [cite: 2026-01-16]")

    with st.sidebar:
        st.subheader("🖼️ ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        if src_img: st.session_state.dx_src_bytes = src_img.getvalue()
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        
        st.divider()
        hair_s = st.selectbox("💇 髪型", list(HAIR_STYLES.keys()), key="dx_hs")
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()), key="dx_hc")
        cloth_note = st.text_input("衣装の追加補足", placeholder="例: black satin bunny suit")
        
        st.divider()
        st.subheader("⚙️ 調整")
        id_weight = st.slider("顔の固定強度", 0.0, 1.0, 0.82)
        # 衣装反映と体型維持のため Guidance を 6.0 に固定気味に
        g_scale = st.slider("命令遵守度 (Guidance)", 1.0, 10.0, 6.0)
        
        run_btn = st.button("🚀 DX鉄壁一括生成", type="primary")

    if st.session_state.dx_anchor:
        with st.expander("📝 解析された衣装設計図"): st.code(st.session_state.dx_anchor)

    if run_btn and st.session_state.dx_src_bytes and ref_img:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            # Step 1: Gemini解析（衣装アンカー作成） [cite: 2026-01-16]
            status.info("🕒 Step 1: 衣装のデザインを固定中...")
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            analysis_p = f"Describe the clothing in detail using ONLY keywords. Material, cut, specific colors. No nudity. {cloth_note}"
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, analysis_p])
            st.session_state.dx_anchor = response.text.replace("\n", ", ")

            # Step 2: Fal.ai 描画 [cite: 2026-03-01]
            status.info("⏳ Step 2: キャスト転送中...")
            face_url = fal_client.upload(st.session_state.dx_src_bytes, "image/jpeg")
            poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
            st.session_state.dx_current_poses = poses
            
            for i in range(4):
                status.info(f"🎨 DX鉄壁描画中 ({i+1}/4)... [cite: 2026-01-16]")
                final_p = get_final_dx_prompt(poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c])
                
                try:
                    # PuLIDモデルで一括生成
                    result = generate_with_retry(face_url, final_p, id_weight, g_scale, 35)
                    st.session_state.dx_images[i] = Image.open(requests.get(result['images'][0]['url'], stream=True).raw)
                except Exception as inner_e:
                    st.error(f"枠 {i+1} 失敗: {inner_e}"); break
                progress.progress((i+1)/4)
            status.empty()
            st.rerun()
        except Exception as e:
            st.error(f"システムエラー: {e}")

    # --- 表示エリア：黄金律 UI [cite: 2026-01-16] ---
    if any(img is not None for img in st.session_state.dx_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                img = st.session_state.dx_images[i]
                if img:
                    st.image(img, use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"dx_{i}.jpg", key=f"dl_{i}")
                    if st.button(f"🔄 枠{i+1} 撮り直し", key=f"re_{i}"):
                        with st.spinner("再生成中..."):
                            f_url = fal_client.upload(st.session_state.dx_src_bytes, "image/jpeg")
                            p = get_final_dx_prompt(st.session_state.dx_current_poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c])
                            res = generate_with_retry(f_url, p, id_weight, g_scale, 35)
                            st.session_state.dx_images[i] = Image.open(requests.get(res['images'][0]['url'], stream=True).raw)
                            st.rerun()
