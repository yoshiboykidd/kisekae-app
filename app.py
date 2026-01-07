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
    # secretsからAPIキーを取得
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)

    st.title("📸 AI KISEKAE [Stable & Professional]")

    # 4つの構図を物理的に定義（ポーズ被り対策）
    POSE_SLOTS = {
        "A: 立ち姿（全身正面）": "A full-body photograph of the person standing perfectly upright, facing the camera directly. The entire outfit is visible.",
        "B: 動きのある姿（全身）": "A dynamic full-body photograph capturing a natural movement like walking or a slight turn, adding energy to the photo.",
        "C: 座り姿（全身）": "A full-body photograph of the person sitting gracefully on a sofa or luxury chair. Legs are crossed or tucked naturally.",
        "D: バストアップ（顔寄り）": "A portrait photograph focusing from the chest up. Highlighting the face, makeup, and the upper detail of the outfit."
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. キャスト写真 (顔用・必須)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装参照写真 (柄・素材用)", type=['png', 'jpg', 'jpeg'])
        
        st.divider()
        cloth_main = st.selectbox("3. 基本スタイル", ["リゾートビキニ", "タイトミニドレス", "清楚ワンピース", "ナース服", "バニーガール", "メイド服", "浴衣"])
        cloth_detail = st.text_input("衣装の追加指示", placeholder="例：黒のレース素材、フリル多め")
        
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "ビーチ"])
        
        st.divider()
        run_button = st.button("✨ 4ポーズを一括生成")

    if run_button and source_img:
        st.subheader("🖼️ 生成結果")
        
        # 2x2のグリッドレイアウトを作成
        cols_row1 = st.columns(2)
        cols_row2 = st.columns(2)
        placeholders = [cols_row1[0], cols_row1[1], cols_row2[0], cols_row2[1]]

        # AIに渡す画像パーツの準備
        base_parts = [types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        for i, (slot_name, pose_instruction) in enumerate(POSE_SLOTS.items()):
            with placeholders[i]:
                with st.spinner(f"生成中: {slot_name}"):
                    try:
                        # 衣装指示の構築
                        if ref_img:
                            cloth_task = (
                                f"OUTFIT: Replicate the color, pattern, and texture from IMAGE 2 exactly onto a {cloth_main}. {cloth_detail}."
                            )
                        else:
                            cloth_task = f"OUTFIT: A high-quality {cloth_main}. {cloth_detail}."

                        # プロンプトの構築
                        prompt = (
                            f"TASK: Generate a professional photo based on these images. "
                            f"IDENTITY: Strictly use the facial features and identity from IMAGE 1. "
                            f"OUTFIT REFERENCE: If IMAGE 2 is present, use its design DNA. "
                            f"COMPOSITION: {pose_instruction} "
                            f"{cloth_task} "
                            f"BACKGROUND: {bg} with professional bokeh blur. "
                            f"EXPRESSION: Lips sealed together, elegant look. No teeth visible. "
                            f"QUALITY: 8k, photorealistic masterpiece, sharp focus on the person."
                        )

                        response = client.models.generate_content(
                            model='gemini-3-pro-image-preview',
                            contents=base_parts + [prompt],
                            config=types.GenerateContentConfig(
                                response_modalities=['IMAGE'],
                                safety_settings=[
                                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                                ],
                                image_config=types.ImageConfig(aspect_ratio="2:3")
                            )
                        )

                        if response.candidates and response.candidates[0].content.parts:
                            img_data = response.candidates[0].content.parts[0].inline_data.data
                            img = Image.open(io.BytesIO(img_data)).resize((600, 900))
                            st.image(img, caption=slot_name, use_container_width=True)
                            
                            # ダウンロード用バッファ
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p_{i+1}.jpg", mime="image/jpeg", key=f"dl_{i}")
                        else:
                            st.error("生成失敗: フィルターまたはエラー")
                    except Exception as e:
                        st.error(f"システムエラー: {e}")
                    
                    # 連続リクエストによるエラー防止
                    time.sleep(1.2)

st.markdown("---")
st.caption("© 2026 Karinto Group - Identity & Consistency Engine")
