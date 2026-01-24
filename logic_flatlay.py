import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 安定生成エンジン (Mainと共通の地雷回避ロジック) ---
def generate_flatlay_stable(client, contents, prompt, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            # 安定版の最小構成 Config
            response = client.models.generate_content(
                model='gemini-3-pro-image-preview',
                contents=contents + [prompt],
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE'],
                    safety_settings=[
                        types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')
                    ]
                )
            )
            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].inline_data.data
        except Exception as e:
            if "503" in str(e) and attempt < max_retries:
                time.sleep(2); continue
            return str(e)
    return "FAILED"

def show_flatlay_ui():
    st.header("👕 洋服アンカー制作 (Sub System)")
    st.write("複雑な衣装を、KISEKAE Mainで使いやすい『綺麗な設計図』に変換します。")
    
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    # バイトデータ保持用の初期化
    if "flat_ref_bytes" not in st.session_state: st.session_state.flat_ref_bytes = None

    with st.sidebar:
        ref_img = st.file_uploader("元の衣装画像", type=['png', 'jpg', 'jpeg'], key="f_src")
        if ref_img:
            st.session_state.flat_ref_bytes = ref_img.getvalue()
            st.image(ref_img, caption="元画像プレビュー", use_container_width=True)
        
        desc = st.text_input("衣装の特徴（素材・色）", "サテン、光沢のあるシルク、細かいレース")
        run_btn = st.button("🚀 アンカー画像を生成", type="primary")

    if run_btn and st.session_state.flat_ref_bytes:
        with st.spinner("高品質な設計図を生成中..."):
            # アスペクト比 1:1 はプロンプト内で指示
            prompt = (
                f"Professional catalog shot of a clothing flat lay: {desc}. "
                f"Neutral grey background, industrial textile scan quality, 1:1 square aspect ratio."
            )
            
            contents = [types.Part.from_bytes(data=st.session_state.flat_ref_bytes, mime_type='image/jpeg')]
            res_data = generate_flatlay_stable(client, contents, prompt)
            
            if isinstance(res_data, bytes):
                img = Image.open(io.BytesIO(res_data))
                st.success("✨ 設計図（アンカー）の生成に成功しました")
                st.image(img, caption="この画像を保存して Main の IMAGE 2 で使用してください", use_container_width=True)
                
                # ダウンロードボタン
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.download_button("💾 アンカー画像を保存", buf.getvalue(), "clothing_anchor.png", "image/png")
            else:
                st.error(f"生成失敗: {res_data}")
