import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 認証機能 (合言葉: karin10) ---
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

    st.title("📸 AI KISEKAE [Identity Lock V1]")

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        src_img = st.file_uploader("1. キャスト写真 (顔・骨格：絶対遵守)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装写真 (あればこの服を100%着せる)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル (参考画像なし時のみ有効)", ["ワンピースドレス", "タイトミニドレス", "ナースウェア", "メイドウェア", "サマーウェア", "浴衣"])
        cloth_detail = st.text_input("追加指示", placeholder="例：黒サテン地、ピンクのリボン")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "サマーリゾート"])
        st.divider()
        run_button = st.button("✨ 4枚一括生成")

    if run_button and src_img:
        st.subheader("🖼️ 生成結果")
        cols_row1 = st.columns(2)
        cols_row2 = st.columns(2)
        placeholders = [cols_row1[0], cols_row1[1], cols_row2[0], cols_row2[1]]

        base_parts = [types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # --- シンプルな主従ロジック ---
        # 参照画像(Image 2)がある場合は、セレクトボックスの項目を無視する
        if ref_img:
            outfit_cmd = f"WEAR THE EXACT CLOTHES FROM IMAGE 2. {cloth_detail}."
        else:
            outfit_cmd = f"WEAR A {cloth_main}. {cloth_detail}."

        # 命令の優先順位を「Identity」に一点集中
        prompt = (
            f"ABSOLUTE RULE: Subject is the person in IMAGE 1. Face and bone structure must be 100% identical to IMAGE 1. "
            f"IGNORE the face in IMAGE 2. "
            f"RULE: Lips sealed, no teeth. "
            f"OUTFIT: {outfit_cmd} "
            f"TASK: 2x2 grid of 4 poses (Standing, Walking, Sitting, Close-up). "
            f"Background: {bg}. Photorealistic 8k."
        )

        with st.spinner("キャストの顔を固定して生成中..."):
            try:
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=base_parts + [prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')],
                        image_config=types.ImageConfig(aspect_ratio="2:3")
                    )
                )

                if response.candidates and response.candidates[0].content.parts:
                    grid_data = response.candidates[0].content.parts[0].inline_data.data
                    full_img = Image.open(io.BytesIO(grid_data))
                    w, h = full_img.size
                    
                    # 4分割の座標設定
                    coords = [
                        (0, 0, w//2, h//2),     # 左上
                        (w//2, 0, w, h//2),     # 右上
                        (0, h//2, w//2, h),     # 左下
                        (w//2, h//2, w, h)      # 右下
                    ]
                    
                    for i, coord in enumerate(coords):
                        with placeholders[i]:
                            # 切り出して2:3の縦長にリサイズして表示
                            cropped = full_img.crop(coord).resize((600, 900))
                            st.image(cropped, use_container_width=True)
                            
                            buf = io.BytesIO()
                            cropped.save(buf, format="JPEG")
                            st.download_button(
                                label=f"保存 {i+1}", 
                                data=buf.getvalue(), 
                                file_name=f"p{i+1}.jpg", 
                                mime="image/jpeg", 
                                key=f"dl_btn_{i}"
                            )
                else:
                    st.error("AI規制によりブロックされました。マイルドな表現でお試しください。")
            except Exception as e:
                st.error(f"エラー: {e}")

st.markdown("---")
st.caption("© 2026 Karinto Group - Identity Lock V1")
