import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os
from PIL import Image

# --- 1. 定義データ (日本人女性・実写特化) ---
HAIR_STYLES = {"元画像のまま": "keep original hair", "ゆるふあ巻き": "soft wavy curls", "ハーフアップ": "half-up", "ツインテール": "twin tails", "ポニーテール": "ponytail", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "keep original color", "ナチュラルブラック": "black", "ダークブラウン": "dark brown", "ashベージュ": "ash beige"}

# --- 2. プロンプトエンジン (衣装の塗りつぶし特化) ---
def get_fill_prompt(anchor_text, hair_s, hair_c):
    """元画像の体型を維持しつつ、衣装だけを馴染ませるプロンプト [cite: 2026-01-16]"""
    return (
        f"A Japanese woman wearing {anchor_text}. {hair_s}, {hair_c}. "
        "Hyper-realistic photography, high-quality fabric texture, 8k photo, "
        "seamless integration with the original body, cinematic lighting, film grain [cite: 2026-01-16]."
    )

# --- 3. UI メイン処理 ---
def show_dx_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_anchor" not in st.session_state: st.session_state.dx_anchor = ""

    st.header("💎 AI KISEKAE DX v3.31 (Fill Mode)")
    st.caption("【DX仕様】キャストの体型を100%維持し、衣装だけを書き換えます [cite: 2026-03-01]")

    with st.sidebar:
        st.subheader("🖼️ ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        
        st.divider()
        st.subheader("💇 スタイル設定")
        hair_s = st.selectbox("髪型", list(HAIR_STYLES.keys()), key="dx_hs")
        hair_c = st.selectbox("髪色", list(HAIR_COLORS.keys()), key="dx_hc")
        cloth_note = st.text_input("衣装の追加補足", placeholder="例: black satin bunny suit")
        
        st.divider()
        g_scale = st.slider("書き換え強度 (Guidance)", 1.0, 30.0, 15.0, help="高いほど衣装がIMAGE2に近づきます。")
        
        run_btn = st.button("🚀 DX鉄壁一括着せ替え", type="primary")

    if run_btn and src_img and ref_img:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            # Step 1: 衣装解析
            status.info("🕒 Step 1: 衣装デザインを解析中...")
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            analysis_p = f"Describe clothing ONLY in keywords. {cloth_note}"
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, analysis_p])
            st.session_state.dx_anchor = response.text.replace("\n", ", ")

            # Step 2: Fal.ai Flux-Fill (衣装部分のみを書き換え)
            status.info("⏳ Step 2: キャストの体型を維持したまま着せ替え中...")
            src_url = fal_client.upload(src_img.getvalue(), "image/jpeg")
            
            for i in range(4):
                status.info(f"🎨 着せ替え中 ({i+1}/4)...")
                final_p = get_fill_prompt(st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c])
                
                try:
                    # mask_prompt機能を使って、AIに「服の場所」を自動認識させる [cite: 2026-03-01]
                    result = fal_client.subscribe(
                        "fal-ai/flux/v1/fill",
                        arguments={
                            "image_url": src_url,
                            "prompt": final_p,
                            "mask_prompt": "clothing, clothes, outfit, dress", # ここが肝
                            "guidance_scale": g_scale,
                            "num_inference_steps": 30,
                            "enable_safety_checker": False
                        }
                    )
                    image_url = result['images'][0]['url']
                    st.session_state.dx_images[i] = Image.open(requests.get(image_url, stream=True).raw)
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
                if st.session_state.dx_images[i]:
                    st.image(st.session_state.dx_images[i], use_container_width=True)
                    buf = io.BytesIO(); st.session_state.dx_images[i].save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"dx_{i}.jpg", key=f"dl_{i}")
