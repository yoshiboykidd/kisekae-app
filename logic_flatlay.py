import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義 (v2.3: 除外指示の反映を強化) ---
VERSION = "2.3"
FLAT_LAY_PROMPT_BASE = (
    "A high-end professional fashion catalog flat lay photography of a SINGLE standalone garment. "
    "Shot from a direct top-down bird's-eye view, perfectly centered on a seamless, solid pure white studio background (#FFFFFF). "
    "High-key studio lighting, no harsh shadows, extremely sharp focus. "
    "8k resolution, photorealistic fabric textures. "
    "STRICT RULE: Only the selected clothing. NO humans, NO body parts, NO mannequins."
)

def show_flatlay_ui():
    st.header(f"👕 洋服アンカー制作 (v{VERSION})")
    st.info("特定のアイテム（カバン・靴・装飾品など）を除外して、服だけを抽出できます。")
    
    # APIクライアントの初期化
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    if "flat_ref_bytes" not in st.session_state: 
        st.session_state.flat_ref_bytes = None

    with st.sidebar:
        st.header("📸 抽出・除外設定")
        ref_img = st.file_uploader("元の衣装画像", type=['png', 'jpg', 'jpeg'], key="f_src")
        
        if ref_img:
            st.session_state.flat_ref_bytes = ref_img.getvalue()
            st.image(ref_img, caption="解析対象", use_container_width=True)
        
        # ★追加：何を除外するかを指示する入力欄
        exclude_text = st.text_input(
            "除外したいもの", 
            placeholder="例：カバン、靴、帽子、ネックレス",
            help="画像に写っているが、アンカー画像には含めたくないものを入力してください。"
        )
        
        category = st.selectbox("アイテムの種類", [
            "Casual fashion", "Night-fashion", "Satin slip", "Silk camisole", "Business suit", "Swimwear"
        ])
        
        st.divider()
        run_btn = st.button("🚀 特定アイテムのみ精密生成", type="primary")

    if run_btn and st.session_state.flat_ref_bytes:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. AI解析結果")
            with st.spinner("指定アイテムを除外してスキャン中..."):
                try:
                    input_img_part = types.Part.from_bytes(
                        data=st.session_state.flat_ref_bytes, 
                        mime_type='image/jpeg'
                    )
                    
                    # 除外指示を解析プロンプトに組み込む
                    analysis_prompt = (
                        f"Analyze the {category} in this image. "
                        f"STRICT RULE: COMPLETELY IGNORE and EXCLUDE these items: {exclude_text}. "
                        "Focus only on the main garment. Describe its material, color, and structure "
                        "for a professional 8k flat-lay reconstruction."
                    )
                    
                    analysis_res = client.models.generate_content(
                        model='gemini-2.0-flash', 
                        contents=[analysis_prompt, input_img_part]
                    )
                    clothing_desc = analysis_res.text
                    
                    st.success("✅ 不要な情報を排除して言語化しました")
                    with st.expander("AIのスキャンレポート"):
                        st.write(clothing_desc)
                except Exception as e:
                    st.error(f"解析エラー: {e}")
                    return

        with col2:
            st.subheader("2. 生成された設計図")
            with st.spinner("不要な小物を除外して描画中..."):
                # 生成プロンプトにも除外指示を念押し
                final_gen_prompt = (
                    f"{FLAT_LAY_PROMPT_BASE} \n"
                    f"STRICT NEGATIVE CONSTRAINT: NO {exclude_text}. \n"
                    f"Technical Specification: {clothing_desc}"
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
        if not st.session_state.flat_ref_bytes:
            st.write("画像をアップロードしてください。")
