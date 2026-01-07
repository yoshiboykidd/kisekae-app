import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 認証機能 (karin10) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 Karinto Group Image Tool")
        pwd = st.text_input("合言葉を入力してください", type="password")
        if st.button("ログイン"):
            if pwd == "karin10": 
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("合言葉が正しくありません")
        return False
    return True

# --- 2. メインアプリ ---
if check_password():
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)

    st.title("📸 AI KISEKAE [Perfect Consistency]")

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        src_img = st.file_uploader("1. キャスト写真 (顔用)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装参照写真 (柄・素材用)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル", ["ワンピースドレス", "タイトミニドレス", "オフィスカジュアル", "ナーススタイル", "メイドスタイル", "スイムウェア", "浴衣"])
        cloth_detail = st.text_input("追加指示", placeholder="例：黒サテン、赤リボン")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "プライベートビーチ"])
        st.divider()
        run_button = st.button("✨ 4ポーズ一括生成開始")

    if run_button and src_img:
        # スロット定義
        slots = ["A:正面全身", "B:斜め動き", "C:座り姿", "D:顔寄り"]
        st.subheader("🖼️ 生成結果")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        base_parts = [types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # グリッド生成用プロンプト
        # 1枚の大きな画像の中に4枚を描かせることで、服の質感をAIに固定させます
        prompt = (
            f"TASK: Generate a single 2x2 grid image containing 4 distinct photos of the woman from IMAGE 1. "
            f"IDENTITY: All 4 panels must show the EXACT same face from IMAGE 1. Do NOT use face from IMAGE 2. "
            f"OUTFIT: All 4 panels must wear the IDENTICAL outfit: {cloth_main}, {cloth_detail}. "
            f"REFERENCE: Use color/pattern from IMAGE 2 for ALL panels. "
            f"POSES: Top-Left: Standing front. Top-Right: Walking side. Bottom-Left: Sitting. Bottom-Right: Close-up face. "
            f"ENVIRONMENT: {bg} with bokeh. MOUTH: Lips sealed, no teeth. "
            f"QUALITY: 8k resolution, professional photography grid, sharp focus."
        )

        with st.spinner("4枚の衣装を統一して生成中..."):
            try:
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=base_parts + [prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')],
                        image_config=types.ImageConfig(aspect_ratio="1:1")
                    )
                )

                if response.candidates and response.candidates[0].content.parts:
                    grid_data = response.candidates[0].content.parts[0].inline_data.data
                    full_img = Image.open(io.BytesIO(grid_data))
                    w, h = full_img.size
                    
                    # 4分割の座標設定
                    coords = [(0, 0, w//2, h//2), (w//2, 0, w, h//2), (0, h//2, w//2, h), (w//2, h//2, w, h)]
                    
                    for i, coord in enumerate(coords):
                        with placeholders[i]:
                            # 切り出してリサイズ
                            cropped = full_img.crop(coord).resize((600, 900))
                            st.image(cropped, caption=slots[i], use_container_width=True)
                            
                            # ダウンロードボタン (構文エラー防止のため簡潔に記述)
                            buf = io.BytesIO()
                            cropped.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p{i+1}.jpg", mime="image/jpeg", key=f"btn_{i}")
                else:
                    st.error("AI規制によりブロックされました。")
            except Exception as e:
                st.error(f"エラー: {e}")

st.markdown("---")
st.caption("© 2026 Karinto Group - Grid Logic V1")
