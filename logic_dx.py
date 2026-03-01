import streamlit as st
import fal_client
import io
from PIL import Image
import requests

# --- 1. 定義データ (DX専用：より写実的な指示をプリセット) ---
DX_DEFAULT_PROMPT = "extreme high quality, photorealistic, 8k, masterpiece, highly detailed skin texture, soft cinematic lighting"

def show_dx_ui():
    # Fal.aiのキーチェック
    if "FAL_KEY" not in st.secrets:
        st.error("🔑 Fal.aiのAPIキーが st.secrets に設定されていません。")
        st.stop()
    
    # 環境変数にセット
    import os
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    st.header("💎 AI KISEKAE DX (Powered by Fal.ai)")
    st.caption("【DX版仕様】検閲なし / PuLID顔固定 / Flux.1 高速エンジン")

    # --- サイドバー構成 ---
    with st.sidebar:
        st.subheader("🖼️ 画像ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1: 顔固定用)", type=['png', 'jpg', 'jpeg'], key="dx_src")
        if src_img:
            st.image(src_img, caption="Face Reference", use_container_width=True)
        
        st.divider()
        st.subheader("👗 衣装設定")
        cloth_detail = st.text_area("衣装・演出の詳細 (English)", 
                                   placeholder="例: wearing a black silk bunny suit, high heels, in a luxury bar",
                                   height=100)
        
        id_weight = st.slider("顔の固定強度 (ID Weight)", 0.0, 1.0, 0.85, help="1.0に近いほど元画像に忠実になります")
        
        st.divider()
        run_btn = st.button("🚀 DX一括生成 (1枚)", type="primary")

    # --- 生成処理 ---
    if run_btn:
        if not src_img:
            st.error("🚫 キャスト画像 (IMAGE 1) をアップロードしてください。")
            st.stop()
        if not cloth_detail:
            st.warning("⚠️ 衣装詳細が空です。デフォルトのプロンプトで生成します。")

        status = st.empty()
        progress = st.progress(0)

        try:
            # Step 1: キャスト画像をFal.aiにアップロード
            status.info("⏳ 画像データを転送中...")
            image_bytes = src_img.getvalue()
            face_url = fal_client.upload(image_bytes, "image/jpeg")
            progress.progress(30)

            # Step 2: 生成リクエスト (Flux-PuLID)
            status.info("🎨 Fal.aiエンジンで描画中 (検閲なしモード)...")
            
            # プロンプトの組み立て
            final_prompt = f"{cloth_detail}, {DX_DEFAULT_PROMPT}"
            
            result = fal_client.subscribe(
                "fal-ai/flux-pulid",
                arguments={
                    "prompt": final_prompt,
                    "reference_image_url": face_url,
                    "id_weight": id_weight,
                    "num_inference_steps": 25,
                    "guidance_scale": 3.5,
                    "image_size": "portrait_4_3",
                    "enable_safety_checker": False  # 【DX版の肝】検閲を完全にオフ
                },
                with_logs=True
            )
            progress.progress(90)

            # Step 3: 結果の表示
            status.empty()
            image_url = result['images'][0]['url']
            
            # 画像をメモリに読み込んで表示 (保存しやすくするため)
            res_img = Image.open(requests.get(image_url, stream=True).raw)
            
            st.image(res_img, caption="✨ DX版 生成結果", use_container_width=True)
            
            # ダウンロードボタン
            buf = io.BytesIO()
            res_img.save(buf, format="JPEG")
            st.download_button("💾 高画質画像を保存", buf.getvalue(), "dx_kisekae.jpg", "image/jpeg")
            
            st.success(f"✅ 生成完了！ (生成時間: {result.get('timings', {}).get('inference', 'N/A'):.2f}秒)")
            progress.progress(100)

        except Exception as e:
            status.error(f"🚫 DX生成エラー: {str(e)}")
            st.info("APIキーやクレジット残高、ネットワーク設定を確認してください。")
