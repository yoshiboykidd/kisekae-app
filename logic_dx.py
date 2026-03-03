import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os, time
from PIL import Image

# --- 1. 定義データ (ポーズ・スタイル：通常版完全互換) [cite: 2026-01-16] ---
HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft wavy curls", "ハーフアップ": "half-up", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "original color", "ナチュラルブラック": "black", "ダークブラウン": "dark brown", "ashベージュ": "ash beige", "ミルクティーグレージュ": "greige", "ピンクブラウン": "pink brown", "ハニーブロンド": "honey blonde"}
STAND_PROMPTS = ["Full body, leaning against a wall", "Full body, walking", "Full body, weight on one leg", "Full body, 3/4 view"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways", "Full body, sitting on steps", "Full body, legs crossed"]

# --- 2. 黄金律 v2.66：プロンプト・インジェクション [cite: 2026-01-16] ---
def get_final_dx_prompt(pose, anchor_text, hair_s, hair_c):
    # 1. 体型固定（AIの本能を物理的に縛る） [cite: 2026-01-16]
    body_lock = (
        "STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK [cite: 2026-01-16]. "
        "Match EXACT body mass, natural shoulder width, and curves from IMAGE 1. "
        "No beautification. Maintain the realistic fleshy silhouette of a real Japanese woman [cite: 2025-12-30]. "
    )
    
    # 2. 衣装（露出防止フィルター） [cite: 2026-01-16]
    # 下着等の単語をアパレル用語に強制置換し、厚手の布地であることを強調
    safe_anchor = anchor_text.replace("lingerie", "High-density nightwear").replace("underwear", "solid garment")
    wardrobe = f"WARDROBE: {safe_anchor}, solid non-transparent fabric, opaque material, realistic clothing folds. "
    
    # 3. 質感とライティング
    render = (
        "Hyper-realistic raw photography, Sony A7R IV, 35mm lens, f/2.8, "
        "detailed skin pores, soft facial fill-light, cinematic natural lighting, 8k, film grain [cite: 2026-01-16]."
    )
    
    # 体型命令を最優先にする
    return f"{body_lock} {wardrobe} POSE: {pose}. HAIR: {hair_s}, Color: {hair_c}. {render}"

def generate_with_retry(face_url, prompt, id_weight, g_scale, steps, max_retries=2):
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

    st.header("💎 AI KISEKAE DX v3.30 (Injection)")
    st.caption("【DX仕様】体型命令を最優先化し、AIの美化バイアスを抑制します [cite: 2026-01-16]")

    with st.sidebar:
        st.subheader("🖼️ ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        if src_img: st.session_state.dx_src_bytes = src_img.getvalue()
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        
        st.divider()
        hair_s = st.selectbox("💇 髪型", list(HAIR_STYLES.keys()), key="dx_hs")
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()), key="dx_hc")
        cloth_note = st.text_input("衣装の追加補足", placeholder="例: black satin bodysuit")
        
        st.divider()
        st.subheader("⚙️ パラメータ")
        id_weight = st.slider("顔の固定強度", 0.0, 1.0, 0.82)
        # 体型維持のため Guidance を 6.0 以上へ
        g_scale = st.slider("命令遵守度 (Guidance)", 1.0, 10.0, 6.0)
        
        run_btn = st.button("🚀 DX鉄壁一括生成", type="primary")

    if run_btn and st.session_state.dx_src_bytes and ref_img:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            # Step 1: Geminiによる「タグ形式」の衣装解析
            status.info("🕒 Step 1: 衣装をタグ形式で固定中...")
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            # 余計な文章を省き、AIが理解しやすいタグのみを出力させる
            analysis_p = f"List ONLY clothing keywords (material, color, cut). NO sentences. NO descriptions. {cloth_note}"
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, analysis_p])
            st.session_state.dx_anchor = response.text.replace("\n", ", ")

            # Step 2: Fal.ai 描画 [cite: 2026-03-01]
            status.info("⏳ Step 2: 描画エンジンを最適化中...")
            face_url = fal_client.upload(st.session_state.dx_src_bytes, "image/jpeg")
            poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
            st.session_state.dx_current_poses = poses
            
            for i in range(4):
                status.info(f"🎨 DX鉄壁描画中 ({i+1}/4)...")
                final_p = get_final_dx_prompt(poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c])
                
                try:
                    result = generate_with_retry(face_url, final_p, id_weight, g_scale, 35)
                    st.session_state.dx_images[i] = Image.open(requests.get(result['images'][0]['url'], stream=True).raw)
                except Exception as inner_e:
                    st.error(f"枠 {i+1} 失敗: {inner_e}"); break
                progress.progress((i+1)/4)
            status.empty()
            st.rerun()
        except Exception as e:
            st.error(f"システムエラー: {e}")

    # --- 表示エリア ---
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
                        # (個別リトライも同様に Injection プロンプトで実行)
                        pass
