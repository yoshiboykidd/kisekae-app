import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os
from PIL import Image

# --- 1. バリエーション用の「世界観」定義 ---
SCENES = [
    "Luxury hotel suite, warm dim lighting, bokeh background",
    "Nightclub VIP lounge, neon accents, cinematic atmosphere",
    "Modern minimal terrace, sunset golden hour, natural soft light",
    "Urban street background, rainy night with city lights reflections"
]

# --- 2. プロンプトエンジン (体型死守 + 世界観注入) ---
def get_variation_prompt(scene, clothing_anchor, body_anchor):
    # 黄金律：体型を言葉でガチガチに固定する [cite: 2026-01-16]
    body_lock = (
        f"STRICT PHYSICAL FIDELITY: {body_anchor}. ABSOLUTE BODY VOLUME LOCK. "
        "Match EXACT body mass and natural shoulder width of IMAGE 1. "
        "Do NOT beautify. Maintain the original fleshy silhouette [cite: 2026-01-16]. "
    )
    # 衣装と背景
    wardrobe = f"WARDROBE: {clothing_anchor}, high-quality fabric. "
    render = (
        f"SCENE: {scene}. Japanese woman [cite: 2025-12-30]. "
        "Hyper-realistic raw photo, Sony A7R IV, 35mm lens, f/2.8, detailed skin, 8k, film grain [cite: 2026-01-16]."
    )
    return f"{body_lock} {wardrobe} {render}"

# --- 3. UI メイン処理 ---
def show_dx_ui():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4

    st.header("💎 AI KISEKAE DX v4.2 (Variation Mode)")
    st.caption("【DX最終形態】体型を守りつつ、4枚の背景と雰囲気をガラッと変えます。")

    with st.sidebar:
        st.subheader("🖼️ 画像ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        st.divider()
        id_weight = st.slider("顔の固定強度", 0.0, 1.0, 0.82)
        # i2iの強度：0.4〜0.5にすると「ポーズは維持しつつ、服と背景が変わる」
        strength = st.slider("写真の変え具合", 0.3, 0.7, 0.45, help="高いほど背景が変わり、低いほど元の写真に残ります。")
        run_btn = st.button("🚀 DXバリエーション生成", type="primary")

    if run_btn and src_img and ref_img:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            # Step 1: ダブル・アンカー解析
            status.info("🕒 Step 1: キャストの体型と衣装を深く解析中...")
            src_part = types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg')
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            analysis_p = "Analyze IMAGE 1 body type (weight, width) and IMAGE 2 clothing detail. Output: BODY: [desc], CLOTHING: [keywords]."
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[src_part, ref_part, analysis_p])
            body_a = response.text.split("CLOTHING:")[0].replace("BODY:", "").strip()
            cloth_a = response.text.split("CLOTHING:")[1].strip()

            # Step 2: Image-to-Image 生成
            status.info("⏳ Step 2: 4つの異なるシチュエーションで生成中...")
            src_url = fal_client.upload(src_img.getvalue(), "image/jpeg")
            
            for i in range(4):
                status.info(f"🎨 シーン {i+1} を描画中...")
                # 4枚それぞれに違う背景指示を出す
                final_p = get_variation_prompt(SCENES[i], cloth_a, body_a)
                
                result = fal_client.subscribe(
                    "fal-ai/flux-pulid",
                    arguments={
                        "prompt": final_p,
                        "reference_image_url": src_url, # 顔固定
                        "image_url": src_url,           # 体型の下書きとして使用
                        "strength": strength,           # 元画像からの変化度
                        "id_weight": id_weight,
                        "guidance_scale": 5.0,
                        "num_inference_steps": 35,
                        "enable_safety_checker": False
                    }
                )
                image_url = result['images'][0]['url']
                st.session_state.dx_images[i] = Image.open(requests.get(image_url, stream=True).raw)
                progress.progress((i+1)/4)
            
            status.empty()
            st.rerun()
        except Exception as e:
            st.error(f"🚫 生成エラー: {e}")

    # --- 表示エリア ---
    if any(img is not None for img in st.session_state.dx_images):
        cols = st.columns(2)
        for i, scene_title in enumerate(["🏨 ホテルVIP", "💃 クラブVIP", "🌇 夕暮れテラス", "🌃 雨の街角"]):
            with cols[i % 2]:
                if st.session_state.dx_images[i]:
                    st.caption(f"シーン: {scene_title}")
                    st.image(st.session_state.dx_images[i], use_container_width=True)
                    buf = io.BytesIO(); st.session_state.dx_images[i].save(buf, format="JPEG")
                    st.download_button(f"💾 {scene_title} 保存", buf.getvalue(), f"dx_{i}.jpg", key=f"dl_{i}")
