import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 定数定義 (v2.66: 幾何学的整合性と左右対称性の強化) ---
VERSION = "2.66"
FLAT_LAY_PROMPT_BASE = (
    "A technical, high-resolution fashion flat lay. Direct top-down view. "
    "STRICT STRUCTURAL FIDELITY: The garment must maintain a perfect, symmetrical silhouette. "
    "Centrally aligned on a pristine white background. Zero lens distortion. "
    "High-key studio lighting that defines the edges and seams clearly. "
    "8k resolution. Photorealistic material. "
    "NEGATIVE RULE: No distortions, no warped edges, no humans, no bags, no overlapping objects."
)

def show_flatlay_ui():
    st.header(f"👕 洋服アンカー制作 (v{VERSION})")
    st.info("『左右対称スキャン』により、カバンで隠れた部分の形を幾何学的に復元します。")
    
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    if "flat_ref_bytes" not in st.session_state: 
        st.session_state.flat_ref_bytes = None

    with st.sidebar:
        st.header("📸 構造復元設定")
        ref_img = st.file_uploader("元の衣装画像", type=['png', 'jpg', 'jpeg'], key="f_src")
        
        if ref_img:
            st.session_state.flat_ref_bytes = ref_img.getvalue()
            st.image(ref_img, caption="解析対象", use_container_width=True)
        
        st.divider()
        keep_items = st.text_input("🟢 残すもの", value="白いニットワンピース、薄茶色のブーツ")
        remove_items = st.text_input("🔴 完全に消すもの", value="茶色のカバン")
        
        st.divider()
        run_btn = st.button("🚀 幾何学構造を復元して生成", type="primary")

    if run_btn and st.session_state.flat_ref_bytes:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. 幾何学スキャン（骨格抽出）")
            with st.spinner("シルエットの左右対称性を計算中..."):
                try:
                    input_img_part = types.Part.from_bytes(data=st.session_state.flat_ref_bytes, mime_type='image/jpeg')
                    
                    # 【重要】解析プロンプト：幾何学的な「設計図」を定義させる
                    analysis_prompt = (
                        f"Identify the '{keep_items}' in the image while ignoring the '{remove_items}'. "
                        f"CRITICAL TASK: Based on the visible parts of the '{keep_items}', reconstruct its full GEOMETRIC STRUCTURE. "
                        f"Apply SYMMETRY: If one side is hidden by '{remove_items}', mirror the visible side's shape, sleeve length, and neckline. "
                        f"Describe the garment as a 'Technical Blueprint': defining the exact hemline, shoulder width, and cuff shape. "
                        "Output only the structural specifications."
                    )
                    
                    analysis_res = client.models.generate_content(model='gemini-2.0-flash', contents=[analysis_prompt, input_img_part])
                    clothing_desc = analysis_res.text
                    
                    with st.expander("復元された骨格データ"):
                        st.write(clothing_desc)
                except Exception as e:
                    st.error(f"解析エラー: {e}")
                    return

        with col2:
            st.subheader("2. 構造固定されたアンカー")
            with st.spinner("骨格データに基づき再描画中..."):
                # 【重要】生成プロンプト：「対称性の維持」と「歪みの排除」を徹底
                final_gen_prompt = (
                    f"{FLAT_LAY_PROMPT_BASE} \n"
                    f"OBJECTIVE: Render a perfectly symmetrical {keep_items}. \n"
                    f"STRUCTURAL LOCK: Replicate the hemline and neckline exactly as described. \n"
                    f"SYMMETRY MIRRORING: Ensure the left and right sides are balanced and identical in shape. \n"
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
                        st.download_button("💾 構造固定アンカーを保存", img_bytes, f"fixed_anchor_{int(time.time())}.png", "image/png")
                    else:
                        st.error("生成失敗")
                except Exception as e:
                    st.error(f"生成エラー: {str(e)}")
