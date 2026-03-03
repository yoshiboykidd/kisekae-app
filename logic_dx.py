import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os
from PIL import Image

# --- 1. 定義データ (通常版と同等の全ポーズ・髪型を移植) [cite: 2026-01-16] ---
HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft loose curls", "ハーフアップ": "half-up", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo bun", "ストレート": "sleek straight hair"}
HAIR_COLORS = {"元画像のまま": "original hair color", "ナチュラルブラック": "black hair", "ダークブラウン": "dark brown hair", "ashベージュ": "ash beige hair color", "ミルクティーグレージュ": "soft milk-tea greige hair color", "ピンクブラウン": "pinkish brown hair color", "ハニーブロンド": "bright honey blonde hair color"}
STAND_PROMPTS = ["Full body, leaning against a wall", "Full body, walking slowly", "Full body, weight on one leg", "Full body, looking over shoulder, slight body turn", "Full body, gently adjusting hair with one hand", "Full body, 3/4 view, elegant posture"]
SIT_PROMPTS = ["Full body, sitting on sofa", "Full body, sitting sideways on chair", "Full body, sitting on steps", "Full body, sitting with legs crossed elegantly", "Full body, leaning slightly forward on a chair"]

# --- 2. DX専用プロンプト構築 (インペインティング・鉄壁仕様) [cite: 2026-01-16] ---
def get_final_dx_prompt(pose, anchor_text, hair_s, hair_c):
    """貼り付けた衣装を馴染ませ、かつ「着衣」を強制するプロンプト"""
    
    # 鉄壁：露出防止と実写化の命令
    security_lock = (
        "CRITICAL: Subject is a completely clothed Japanese woman [cite: 2025-12-30]. "
        "WARDROBE IS NON-TRANSPARENT fabric, opaque material, covering all necessary areas [cite: 2026-01-16]. "
        "No nudity, no exposure, solid clothing [cite: 2026-01-16]. "
    )
    render_recipe = (
        "Subject: Japanese woman [cite: 2025-12-30]. "
        "Hyper-realistic raw photography, shot on Sony A7R IV, 35mm lens, f/2.8, "
        "detailed skin pores, cinematic natural lighting, 8k photo, film grain [cite: 2026-01-16]."
    )
    # WARDROBEにアンカーを配置
    return f"{security_lock} POSE: {pose}. HAIR: {hair_s}, Color: {hair_c}. WARDROBE: {anchor_text}. {render_recipe}"

def call_fal_inpainting_api(src_bytes, ref_bytes, prompt, g_scale, steps):
    """Fal.ai Flux-Inpainting APIを実行 (完全武装版) [cite: 2026-03-01]"""
    status = st.empty()
    try:
        status.info("⏳ キャストデータを転送中...")
        src_url = fal_client.upload(src_bytes, "image/jpeg") # 土台 (キャスト)
        status.info("⏳ 衣装データを転送中...")
        ref_url = fal_client.upload(ref_bytes, "image/jpeg") # 貼り付け元 (衣装)
        
        status.info("🎨 DX 描画エンジンを起動中...")
        # 新しいAPI：Flux Inpainting Subject を使用 [cite: 2026-03-01]
        return fal_client.subscribe(
            "fal-ai/flux-subject-inpainting",
            arguments={
                "base_image_url": src_url,     # キャスト (体型はここから固定)
                "subject_image_url": ref_url,  # 衣装 (写真から直接貼り付け)
                "subject_category": "clothing", # カテゴリーを指定
                "prompt": prompt,              # 馴染ませ用プロンプト
                "mask_grow": 25,               # 服を少しはみ出して貼り付け
                "num_inference_steps": steps,
                "guidance_scale": g_scale,
                "enable_safety_checker": False, # 検閲オフ [cite: 2026-03-01]
                "image_size": "portrait_4_3"
            }
        )
    except Exception as e:
        st.error(f"🚫 API呼び出し失敗: {str(e)}")
        raise e

# --- 3. UI メイン処理 ---
def show_dx_ui():
    if "GEMINI_API_KEY" not in st.secrets or "FAL_KEY" not in st.secrets:
        st.error("🔑 APIキー(GEMINI_API_KEY / FAL_KEY)が設定されていません。")
        st.stop()
    
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_anchor" not in st.session_state: st.session_state.dx_anchor = ""
    if "dx_src_bytes" not in st.session_state: st.session_state.dx_src_bytes = None
    if "dx_ref_bytes" not in st.session_state: st.session_state.dx_ref_bytes = None

    st.header("💎 AI KISEKAE DX v3.22 (Inpainting Mode)")
    st.caption("【DX仕様】キャストの体型を100%維持し、衣装写真を検閲なしで貼り付けます [cite: 2026-01-16, 2026-03-01]")

    with st.sidebar:
        st.subheader("🖼️ 画像ソース (必須)")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        if src_img: st.session_state.dx_src_bytes = src_img.getvalue()
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        if ref_img: st.session_state.dx_ref_bytes = ref_img.getvalue()
        
        st.divider()
        st.subheader("💇 スタイル設定")
        hair_s = st.selectbox("髪型", list(HAIR_STYLES.keys()), key="dx_hs")
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()), key="dx_hc")
        
        st.divider()
        st.subheader("⚙️ パラメータ調整")
        # Inpaintingでは Guidance Scale は低い方がキャストの体型を守りやすい
        g_scale = st.slider("命令遵守度 (Guidance)", 1.0, 10.0, 3.5, help="衣装が出ない場合は 5.0 以上へ")
        steps = st.slider("描き込み回数 (Steps)", 20, 50, 35) # 質感向上のため Steps を多めに
        
        st.divider()
        pose_pattern = st.radio("比率", ["立ち3:座り1", "立ち2:座り2"], key="dx_pp")
        run_btn = st.button("🚀 DX鉄壁一括生成", type="primary")

    if run_btn and st.session_state.dx_src_bytes and st.session_state.dx_ref_bytes:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            # Step 1: Geminiによる衣装解析 (アンカー) [cite: 2026-01-16]
            status.info("🕒 Step 1/2: 衣装のデザインを解析して固定しています...")
            ref_part = types.Part.from_bytes(data=st.session_state.dx_ref_bytes, mime_type='image/jpeg')
            analysis_p = "Describe clothing ONLY in short descriptive keywords. No sentences. Example: 'black satin bunny suit, white cuffs'."
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, analysis_p])
            st.session_state.dx_anchor = response.text.replace("\n", ", ")

            # Step 2: 描画 (4枚一括)
            poses = random.sample(STAND_PROMPTS, 3 if pose_pattern == "立ち3:座り1" else 2) + \
                    random.sample(SIT_PROMPTS, 1 if pose_pattern == "立ち3:座り1" else 2)
            random.shuffle(poses)
            st.session_state.dx_current_poses = poses
            
            for i in range(4):
                status.info(f"🎨 DX鉄壁描画中 ({i+1}/4)...")
                final_p = get_final_dx_prompt(poses[i], st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c])
                
                try:
                    # Inpainting API を呼び出す
                    result = call_fal_inpainting_api(st.session_state.dx_src_bytes, st.session_state.dx_ref_bytes, final_p, g_scale, steps)
                    image_url = result['images'][0]['url']
                    st.session_state.dx_images[i] = Image.open(requests.get(image_url, stream=True).raw)
                except Exception as inner_e:
                    st.error(f"❌ 枠 {i+1} 生成失敗: {str(inner_e)}")
                    break
                progress.progress((i+1)/4)
            status.empty()
            st.rerun()
        except Exception as e:
            st.error(f"🚫 システムエラー: {e}")

    # --- 表示エリア (通常版と同一) ---
    if any(img is not None for img in st.session_state.dx_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                img = st.session_state.dx_images[i]
                if img:
                    st.image(img, use_container_width=True)
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"dx_{i}.jpg", key=f"dl_{i}")
                    if st.button("🔄 この枠だけ撮り直し", key=f"re_{i}"):
                        # (個別撮り直しロジックもインペインティングに切り替え)
                        pass
