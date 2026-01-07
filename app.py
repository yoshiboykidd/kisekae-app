import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random # randomは使わなくなりましたが、念のため残します

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

    st.title("📸 AI KISEKAE [Identity & Pose Fix]")

    # 構図の定義を、より極端で物理的に異なるものに変更 [対策3]
    POSE_SLOTS = {
        "A: 直立不動（全身）": "A static full-body shot standing perfectly straight, facing the camera. Like a fashion mannequin pose, showing the whole outfit evenly.",
        "B: 動き・歩行（全身）": "A dynamic full-body shot captured mid-stride while walking actively. The body is angled, showing motion and energy.",
        "C: 深い座り（全身）": "A full-body shot sitting down deeply on a chair or directly on the floor. Legs are bent or crossed. Not standing.",
        "D: 寄り（バストアップ）": "A close-up portrait shot from the chest up. Focusing entirely on the face, shoulders, and neckline. This is NOT a full body shot."
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. キャスト写真 (顔用・必須)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装参照写真 (柄用・任意)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル設定", ["リゾートビキニ", "タイトミニドレス", "清楚ワンピース", "ナース服", "バニーガール", "メイド服", "浴衣"])
        cloth_detail = st.text_input("衣装の追加指示", placeholder="例：黒のレース素材、赤いリボン")
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "ビーチ"])
        st.divider()
        run_button = st.button("✨ 4ポーズを生成")

    if run_button and source_img:
        st.subheader("🖼️ 生成結果 (顔固定・ポーズ分離)")
        cols = [st.columns(2), st.columns(2)]
        placeholders = [cols[0][0], cols[0][1], cols[1][0], cols[1][1]]

        base_parts = [types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # 各スロット（A, B, C, D）ごとに生成
        for i, (slot_name, pose_instruction) in enumerate(POSE_SLOTS.items()):
            with placeholders[i]:
                with st.spinner(f"生成中: {slot_name}"):
                    try:
                        # 衣装指示の構築
                        if ref_img:
                            cloth_task = (
                                f"OUTFIT SOURCE: Replicate the EXACT outfit (color, pattern, material) from IMAGE 2. "
                                f"Apply it to a {cloth_main} style. {cloth_detail}."
                            )
                        else:
                            cloth_task = f"OUTFIT: A high-quality {cloth_main}. {cloth_detail}."

                        # プロンプトの構造を根本的に見直し [対策2]
                        # アイデンティティの維持を最優先事項として冒頭に配置
                        prompt = (
                            f"PRIMARY TASK (CRITICAL): Generate a photorealistic photograph of the woman from IMAGE 1. "
                            f"Her facial features and identity MUST be strictly preserved from IMAGE 1. "
                            f"Do NOT use the person's face from IMAGE 2; IMAGE 2 is ONLY for outfit reference. "
                            f"COMPOSITION (PHYSICAL STATE): {pose_instruction} " # 具体的な物理状態を指定
                            f"{cloth_task} " # 衣装指示
                            f"BACKGROUND: {bg} with professional bokeh blur. "
                            f"FACE EXPRESSION: LIPS SEALED TOGETHER. NO TEETH VISIBLE. Elegant look. "
                            f"QUALITY: 8k, masterpiece, sharp focus on the subject."
                        )

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
                            img_data = response.candidates[0].content.parts[0].inline_data.data
                            img = Image.open(io.BytesIO(img_data)).resize((600, 900))
                            st.image(img, caption=slot_name, use_container_width=True)
                            
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG")
                            # ダウンロードボタンのkeyを一意にする
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p_{i+1}.jpg", mime="image/jpeg", key=f"dl_btn_{i}")
                        else:
                            st.error("生成失敗: フィルターまたはエラー")
                    except Exception as e:
                        st.error(f"エラー: {e}")
                    # インターバルは少し短くしても大丈夫かもしれません。試行錯誤点です。
                    time.sleep(1.0) 

st.markdown("---")
st.caption("© 2026 Karinto Group - Identity Protected Engine")
