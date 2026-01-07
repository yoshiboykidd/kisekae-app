import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 認証機能 ---
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

    st.title("📸 AI KISEKAE [Perfect Aspect Ratio]")

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        src_img = st.file_uploader("1. キャスト写真 (顔用)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装参照写真 (柄・素材用)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル", ["ワンピースドレス", "タイトミニドレス", "オフィスカジュアル", "ナーススタイル", "メイドスタイル", "スイムウェア", "浴衣"])
        cloth_detail = st.text_input("追加指示", placeholder="例：黒サテン、赤リボン")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "プライベートビーチ"])
        st.divider()
        run_button = st.button("✨ 黄金比で4枚生成")

    if run_button and src_img:
        # スロット名の定義
        slots = ["正面全身", "斜め動き", "座り姿", "顔寄り"]
        st.subheader("🖼️ 生成結果 (2:3 黄金比)")
        
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        base_parts = [types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # プロンプト：縮尺を狂わせないよう「縦長の4面構成」を明示
        prompt = (
            f"TASK: Generate a single professional photography sheet with a 2x2 grid layout. "
            f"Layout contains 4 distinct portraits of the person from IMAGE 1. "
            f"Each of the 4 panels must be a TALL VERTICAL orientation (2:3 aspect ratio). "
            f"IDENTITY: Strictly preserve the face from IMAGE 1 across all panels. "
            f"OUTFIT: All panels MUST wear the IDENTICAL {cloth_main} based on IMAGE 2. {cloth_detail}. "
            f"POSES: Top-Left: Standing front. Top-Right: Dynamic walking. Bottom-Left: Sitting. Bottom-Right: Beauty close-up. "
            f"ENVIRONMENT: {bg} with bokeh. MOUTH: Lips sealed, no teeth. "
            f"QUALITY: 8k resolution, professional lighting, consistent colors."
        )

        with st.spinner("黄金比で一括生成中..."):
            try:
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=base_parts + [prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')],
                        # ここが重要：全体も2:3にすることで、4分割した際も個々が2:3になる
                        image_config=types.ImageConfig(aspect_ratio="2:3")
                    )
                )

                if response.candidates and response.candidates[0].content.parts:
                    grid_data = response.candidates[0].content.parts[0].inline_data.data
                    full_img = Image.open(io.BytesIO(grid_data))
                    w, h = full_img.size
                    
                    # 4分割の座標（縦長グリッド用）
                    coords = [
                        (0, 0, w//2, h//2),     # 左上
                        (w//2, 0, w, h//2),     # 右上
                        (0, h//2, w//2, h),     # 左下
                        (w//2, h//2, w, h)      # 右下
                    ]
                    
                    for i, coord in enumerate(coords):
                        with placeholders[i]:
                            # 分割して表示
                            cropped = full_img.crop(coord)
                            st.image(cropped, caption=slots[i], use_container_width=True)
                            
                            # ダウンロード
                            buf = io.BytesIO()
                            cropped.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p{i+1}.jpg", mime="image/jpeg", key=f"btn_{i}")
                else:
                    st.error("AI規制によりブロックされました。")
            except Exception as e:
                st.error(f"エラー: {e}")

st.markdown("---")
st.caption("© 2026 Karinto Group - Aspect-Perfect Engine")
