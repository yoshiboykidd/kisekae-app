import streamlit as st
import fal_client
import io, requests, os
from PIL import Image

# --- UI メイン処理 ---
def show_dx_ui():
    if "FAL_KEY" not in st.secrets:
        st.error("🔑 FAL_KEY が Secrets に設定されていません。")
        st.stop()
    
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4

    st.header("💎 AI KISEKAE DX v4.0 (IDM-VTO)")
    st.caption("【DX最終仕様】描き直しではなく「試着（画像転送）」モデルを使用します。")

    with st.sidebar:
        st.subheader("🖼️ 画像ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        
        st.divider()
        st.subheader("⚙️ 試着設定")
        category = st.selectbox("衣装の種類", ["upper_body", "lower_body", "dresses"], index=2)
        steps = st.slider("試着精度 (Steps)", 20, 40, 30)
        
        run_btn = st.button("🚀 DXバーチャル試着", type="primary")

    if run_btn and src_img and ref_img:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            status.info("⏳ データを転送中...")
            src_url = fal_client.upload(src_img.getvalue(), "image/jpeg")
            ref_url = fal_client.upload(ref_img.getvalue(), "image/jpeg")
            
            # IDM-VTO モデルによる「直接転送」
            # このモデルは 4枚一括ではなく 1回で最高の 1枚を作るタイプです
            for i in range(4):
                status.info(f"👗 試着中 ({i+1}/4)...")
                # シード値を変えて 4パターン作成
                result = fal_client.subscribe(
                    "fal-ai/idm-vto",
                    arguments={
                        "human_image_url": src_url,     # キャスト
                        "garment_image_url": ref_url,   # 衣装
                        "garment_description": "clothing", 
                        "category": category,
                        "num_inference_steps": steps,
                        "seed": random.randint(0, 999999)
                    }
                )
                image_url = result['image']['url']
                st.session_state.dx_images[i] = Image.open(requests.get(image_url, stream=True).raw)
                progress.progress((i+1)/4)
            
            status.empty()
            st.rerun()

        except Exception as e:
            st.error(f"🚫 試着エラー: {e}")

    # --- 表示エリア ---
    if any(img is not None for img in st.session_state.dx_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                if st.session_state.dx_images[i]:
                    st.image(st.session_state.dx_images[i], use_container_width=True)
                    buf = io.BytesIO(); st.session_state.dx_images[i].save(buf, format="JPEG")
                    st.download_button(f"💾 枠{i+1} 保存", buf.getvalue(), f"vto_{i}.jpg", key=f"dl_{i}")
