import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義 (v2.5: 「孤立と純粋性」を極限まで強調) ---
VERSION = "2.5"
FLAT_LAY_PROMPT_BASE = (
    "A clinical, high-end fashion product scan. Direct top-down view. "
    "The subject is perfectly isolated on a vast, seamless pure white void (#FFFFFF). "
    "Zero distracting elements. No overlapping objects. High-key studio lighting. "
    "STRICT RULE: Only the target garment is physically present. "
    "The background must be completely empty and pristine where other items were previously located."
)

def show_flatlay_ui():
    st.header(f"👕 洋服アンカー制作 (v{VERSION})")
    st.info("『消去指示』ではなく『対象物の独占描画』に切り替え、不要な重なりを強制排除します。")
    
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
        keep_items = st.text_input("🟢 残したいもの（主役）", placeholder="例：白いニット、薄茶色のブーツ")
        remove_items = st.text_input("🔴 存在を消すもの（透明化）", placeholder="例：茶色のカバン")
        
        st.divider()
        run_btn = st.button("🚀 障害物を排除して生成", type="primary", disabled=not (keep_items and remove_items))

    if run_btn and st.session_state.flat_ref_bytes:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. AI解析（遮蔽物の透過処理）")
            with st.spinner("重なりを透過して服の続きを予測中..."):
                try:
                    input_img_part = types.Part.from_bytes(data=st.session_state.flat_ref_bytes, mime_type='image/jpeg')
                    
                    # 【重要】解析プロンプト：「消せ」ではなく「その下にあるはずの服を描写せよ」と指示
                    analysis_prompt = (
                        f"Look at the '{keep_items}' in the image. "
                        f"Notice that '{remove_items}' is obstructing it. "
                        f"TASK: Imagine the '{remove_items}' is invisible. Describe the continuous texture and shape of the '{keep_items}' "
                        f"that should exist underneath where the '{remove_items}' is currently placed. "
                        f"Describe ONLY the '{keep_items}' as if it were the only object in the world."
                    )
                    
                    analysis_res = client.models.generate_content(model='gemini-2.0-flash', contents=[analysis_prompt, input_img_part])
                    clothing_desc = analysis_res.text
                    
                    with st.expander("AIによる透過解析レポート"):
                        st.write(clothing_desc)
                except Exception as e:
                    st.error(f"解析エラー: {e}")
                    return

        with col2:
            st.subheader("2. 完成したアンカー")
            with st.spinner("純粋な対象物のみを描画中..."):
                # 【重要】生成プロンプト：remove_itemsを「描かない」のではなく「背景で上書きする」指示
                final_gen_prompt = (
                    f"{FLAT_LAY_PROMPT_BASE} \n"
                    f"EXCLUSIVE SUBJECT: {keep_items}. \n"
                    f"PLACEMENT: The '{keep_items}' is laid out alone on the white floor. \n"
                    f"VOID AREA: The space previously occupied by '{remove_items}' is now replaced by the clean texture of '{keep_items}' and white background. \n"
                    f"DETAILS: {clothing_desc}"
                )
                
                try:
                    gen_response = client.models.generate_image(
                        model='imagen-4.0-generate-001',
                        prompt=final_gen_prompt,
                        config=types.GenerateImageConfig(aspect_ratio="3:4", output_mime_type='image/png')
                    )

                    if gen_response.generated_images:
                        img_bytes = gen_response.generated_images[0].image.image_bytes
                        st.image(Image.open(io.BytesIO(img_bytes)), use_container_width=True)
                        st.download_button("💾 アンカーを保存", img_bytes, f"anchor_{int(time.time())}.png", "image/png")
                    else:
                        st.error("生成失敗")
                except Exception as e:
                    st.error(f"生成エラー: {str(e)}")
