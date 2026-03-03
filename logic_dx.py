import streamlit as st
import fal_client
import io
import requests
import random
import os
from PIL import Image

# --- 1. 定義データ (ポーズ・スタイル：日本人女性特化) ---
STAND_PROMPTS = [
    "Full body, leaning against a wall", "Full body, walking slowly", 
    "Full body, weight on one leg", "Full body, looking over shoulder, slight body turn", 
    "Full body, gently adjusting hair with one hand", "Full body, 3/4 view, elegant posture", 
    "Full body, hands clasped gently in front"
]
SIT_PROMPTS = [
    "Full body, sitting on sofa", "Full body, sitting sideways on chair", 
    "Full body, sitting on steps", "Full body, sitting with legs crossed elegantly", 
    "Full body, leaning slightly forward on a chair", "Full body, sitting and looking away slightly", 
    "Full body, sitting on a high stool, one leg down"
]

# --- 2. 共通プロンプト生成エンジン (黄金律の移植) ---
def get_dx_prompt(pose_text, wardrobe_detail):
    """顔と体型を同時に死守するための最強プロンプトを組み立てる"""
    # 黄金律：顔の同一性と体積の固定
    identity_prefix = (
        "CRITICAL: ABSOLUTE FACIAL IDENTITY LOCK. "
        "STRICT PHYSICAL FIDELITY: ABSOLUTE BODY VOLUME LOCK. "
        "1. FACE: Replicate EXACT face from IMAGE 1. 1:1 identity match, skeletal, eye, nose, mouth match. "
        "2. PHYSICAL: Match the exact body mass, shoulder width, and curves of IMAGE 1. "
        "Do not beautify or thin the body. Maintain original body volume. "
    )
    # 実写特化：イラスト感を消すためのレシピ
    render_suffix = (
        "Subject is a Japanese woman. "
        "Shot on 35mm lens, f/2.8, highly detailed natural skin texture with visible pores, "
        "soft facial fill-light, neutral expression, 8k cinematic photo, film grain."
    )
    return f"{identity_prefix} POSE: {pose_text}. WARDROBE: {wardrobe_detail}. {render_suffix}"

def call_fal_api(face_url, prompt, id_weight):
    """Fal.ai APIを叩く実務関数"""
    return fal_client.subscribe(
        "fal-ai/flux-pulid",
        arguments={
            "prompt": prompt,
            "reference_image_url": face_url,
            "id_weight": id_weight,
            "num_inference_steps": 30,
            "guidance_scale": 4.0, # 体型維持命令を優先させるため少し高め
            "enable_safety_checker": False, # DX版：検閲オフ
            "image_size": "portrait_4_3"
        }
    )

# --- 3. UI メイン処理 ---
def show_dx_ui():
    if "FAL_KEY" not in st.secrets:
        st.error("🔑 st.secrets に FAL_KEY が設定されていません。")
        st.stop()
    
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    # セッション状態の初期化
    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_poses" not in st.session_state: st.session_state.dx_poses = [None] * 4
    if "dx_src_bytes" not in st.session_state: st.session_state.dx_src_bytes = None

    st.header("💎 AI KISEKAE DX ver 3.17")
    st.caption("【DX仕様】検閲解除・PuLID顔体型固定・Flux高速エンジン")

    with st.sidebar:
        st.subheader("🖼️ ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_u")
        if src_img:
            st.session_state.dx_src_bytes = src_img.getvalue()
            st.image(src_img, use_container_width=True)
        
        st.divider()
        st.subheader("👗 衣装設定")
        cloth_detail = st.text_area("詳細 (English)", placeholder="例: black satin bodysuit", height=80)
        id_weight = st.slider("顔の固定強度", 0.0, 1.0, 0.85)
        
        st.divider()
        pose_pattern = st.radio("比率", ["立ち3:座り1", "立ち2:座り2"])
        run_btn = st.button("🚀 DX 4枚一括生成", type="primary")

    if run_btn and st.session_state.dx_src_bytes:
        # 初期化
        st.session_state.dx_images = [None] * 4
        if pose_pattern == "立ち3:座り1":
            st.session_state.dx_poses = random.sample(STAND_PROMPTS, 3) + random.sample(SIT_PROMPTS, 1)
        else:
            st.session_state.dx_poses = random.sample(STAND_PROMPTS, 2) + random.sample(SIT_PROMPTS, 2)
        random.shuffle(st.session_state.dx_poses)

        status = st.empty(); progress = st.progress(0)
        
        try:
            status.info("⏳ キャストデータを転送中...")
            face_url = fal_client.upload(st.session_state.dx_source_bytes if hasattr(st.session_state, 'dx_source_bytes') else st.session_state.dx_src_bytes, "image/jpeg")
            
            for i in range(4):
                status.info(f"🎨 DX描画中 ({i+1}/4)...")
                prompt = get_dx_prompt(st.session_state.dx_poses[i], cloth_detail)
                
                try:
                    result = call_fal_api(face_url, prompt, id_weight)
                    image_url = result['images'][0]['url']
                    st.session_state.dx_images[i] = Image.open(requests.get(image_url, stream=True).raw)
                except Exception as inner_e:
                    st.warning(f"⚠️ 枠 {i+1} で中断されました。成功分を表示します。")
                    st.sidebar.error(f"DXエラー: {str(inner_e)}")
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
                                face_u = fal_client.upload(st.session_state.dx_src_bytes, "image/jpeg")
                                prompt = get_dx_prompt(st.session_state.dx_poses[i], cloth_detail)
                                result = call_fal_api(face_u, prompt, id_weight)
                                st.session_state.dx_images[i] = Image.open(requests.get(result['images'][0]['url'], stream=True).raw)
                                st.rerun()
                            except Exception as e:
                                st.error(f"再生成失敗: {str(e)}")
