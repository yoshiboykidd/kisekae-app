import streamlit as st
import fal_client
import io, requests, os, random
from PIL import Image

# --- UI メイン処理 ---
def show_dx_ui():
    if "FAL_KEY" not in st.secrets:
        st.error("🔑 FAL_KEY が Secrets に設定されていません。")
        st.stop()
    
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4

    st.header("💎 AI KISEKAE DX v4.02 (IDM-VTON)")
    st.caption("【DX最終仕様】画像ベースの試着モデルで、体型を100%維持します")

    with st.sidebar:
        st.subheader("🖼️ 画像ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        
        st.divider()
        st.subheader("⚙️ 試着設定")
        # IDM-VTON では詳細な説明（description）が精度を左右します
        cloth_desc = st.text_input("衣装の短い説明", placeholder="例: black lace babydoll")
        
        run_btn = st.button("🚀 DXバーチャル試着を開始", type="primary")

    if run_btn and src_img and ref_img:
        st.session_state.dx_images = [None] * 4
        status = st.empty(); progress = st.progress(0)
        
        try:
            status.info("⏳ 試着エンジン (IDM-VTON) を起動中...")
            src_url = fal_client.upload(src_img.getvalue(), "image/jpeg")
            ref_url = fal_client.upload(ref_img.getvalue(), "image/jpeg")
            
            for i in range(4):
                status.info(f"👗 物理試着中 ({i+1}/4)... 体型を固定しています")
                
                # 正しいモデルID: fal-ai/idm-vton
                # パラメータも IDM-VTON の公式仕様に合わせました
                result = fal_client.subscribe(
                    "fal-ai/idm-vton",
                    arguments={
                        "human_image_url": src_url,     # キャスト (体型ベース)
                        "garment_image_url": ref_url,   # 衣装 (ピクセル転送)
                        "description": cloth_desc if cloth_desc else "clothing",
                        "seed": random.randint(0, 999999)
                    }
                )
                image_url = result['image']['url']
                st.session_state.dx_images[i] = Image.open(requests.get(image_url, stream=True).raw)
                progress.progress((i+1)/4)
            
            status.success("✅ キャストの体型を維持したまま試着が完了しました！")
            st.rerun()

        except Exception as e:
            st.error(f"🚫 試着エラー: {e}")
            if "not found" in str(e).lower():
                st.warning("⚠️ APIのパスが変更されている可能性があります。最新の fal-ai/idm-vton を確認してください。")

    # --- 表示エリア ---
    if any(img is not None for img in st.session_state.dx_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                if st.session_state.dx_images[i]:
                    st.image(st.session_state.dx_images[i], use_container_width=True)
                    buf = io.BytesIO(); st.session_state.dx_images[i].save(buf, format="JPEG")
                    st.download_button(f"💾 枠{i+1} 保存", buf.getvalue(), f"vto_{i}.jpg", key=f"dl_{i}")
