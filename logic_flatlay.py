import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義 (v2.4: 対象物の分離精度を強化) ---
VERSION = "2.4"
FLAT_LAY_PROMPT_BASE = (
    "A high-end professional fashion catalog flat lay photography. "
    "Shot from a direct top-down bird's-eye view, centered on a seamless pure white studio background. "
    "High-key studio lighting, extremely sharp focus, 8k resolution. "
    "STRICT RULE: Only the specified target items are present. No humans, no mannequins."
)

def show_flatlay_ui():
    st.header(f"👕 洋服アンカー制作 (v{VERSION})")
    st.info("「残したいもの」と「消したいもの」を明記することで、色が似ていても正確に分離します。")
    
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    if "flat_ref_bytes" not in st.session_state: 
        st.session_state.flat_ref_bytes = None

    with st.sidebar:
        st.header("📸 抽出・分離設定")
        ref_img = st.file_uploader("元の衣装画像", type=['png', 'jpg', 'jpeg'], key="f_src")
        
        if ref_img:
            st.session_state.flat_ref_bytes = ref_img.getvalue()
            st.image(ref_img, caption="解析対象", use_container_width=True)
        
        st.divider()
        st.write("👇 **ここが重要です** 👇")
        # ★変更点：ポジティブ（残す）とネガティブ（消す）を分離
        keep_items = st.text_input(
            "🟢 残したいもの（主役）", 
            placeholder="例：白いニットワンピース、薄茶色のブーツ",
            help="アンカー画像に必要なアイテムをすべて書いてください。"
        )
        remove_items = st.text_input(
            "🔴 消したいもの（除外）", 
            placeholder="例：茶色のカバン、背景の雑貨",
            help="色が似ていても、ここに書かれたものは強制的に削除します。"
        )
        
        category = st.selectbox("メインアイテムの種類（参考）", ["Casual fashion", "Business suit", "Swimwear", "Other"])
        
        st.divider()
        run_btn = st.button("🚀 精密分離で生成を実行", type="primary", disabled=not (keep_items and remove_items))
        if not (keep_items and remove_items) and ref_img:
            st.caption("※「残したいもの」と「消したいもの」の両方を入力してください。")

    if run_btn and st.session_state.flat_ref_bytes:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. AI解析結果（分離認識）")
            with st.spinner(f"「{keep_items}」と「{remove_items}」を識別分離中..."):
                try:
                    input_img_part = types.Part.from_bytes(
                        data=st.session_state.flat_ref_bytes, 
                        mime_type='image/jpeg'
                    )
                    
                    # 解析プロンプト：両者を明確に区別して認識させる
                    analysis_prompt = (
                        f"TASK: Isolate and analyze ONLY the '{keep_items}' from this image. "
                        f"CRITICAL DISTINCTION: You must differentiate the target '{keep_items}' from the excluded '{remove_items}', even if their colors are similar or overlapping. "
                        f"Completely ignore the material and shape of '{remove_items}'. "
                        f"Describe the visual details (color, texture, shape) of ONLY the '{keep_items}' for reconstruction."
                    )
                    
                    analysis_res = client.models.generate_content(
                        model='gemini-2.0-flash', 
                        contents=[analysis_prompt, input_img_part]
                    )
                    clothing_desc = analysis_res.text
                    
                    st.success("✅ 対象物を識別し、仕様書を作成しました")
                    with st.expander("AIの分離レポートを確認"):
                        st.write(clothing_desc)
                except Exception as e:
                    st.error(f"解析エラー: {e}")
                    return

        with col2:
            st.subheader("2. 完成したアンカー")
            with st.spinner("指定アイテムのみを再構築中..."):
                # 生成プロンプト：何を描き、何を描かないかを明確にする
                final_gen_prompt = (
                    f"{FLAT_LAY_PROMPT_BASE} \n"
                    f"MAIN SUBJECT TO DRAW: {keep_items}. \n"
                    f"STRICT NEGATIVE PROMPT (DO NOT DRAW): {remove_items}. The area where '{remove_items}' was must be clean white background. \n"
                    f"Technical Specs for subject: {clothing_desc}"
                )
                
                try:
                    gen_response = client.models.generate_image(
                        model='imagen-4.0-generate-001',
                        prompt=final_gen_prompt,
                        config=types.GenerateImageConfig(
                            aspect_ratio="3:4", 
                            output_mime_type='image/png'
                        )
                    )

                    if gen_response.generated_images:
                        img_bytes = gen_response.generated_images[0].image.image_bytes
                        st.image(Image.open(io.BytesIO(img_bytes)), use_container_width=True)
                        st.download_button("💾 アンカー画像を保存", img_bytes, f"anchor_{int(time.time())}.png", "image/png")
                    else:
                        st.error("画像が生成されませんでした。")

                except Exception as e:
                    st.error(f"生成エラー (v{VERSION}): {str(e)}")
    else:
        if not st.session_state.flat_ref_bytes and not ref_img:
            st.write("サイドバーから画像をアップロードしてください。")
