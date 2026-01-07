import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

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

    st.title("📸 AI KISEKAE Manager [Master Anchor]")

    # ご提示いただいたVibe別ポーズ集
    POSE_LIBRARY = {
        "Standard (王道)": ["Full body shot, walking toward camera.", "High angle full body shot.", "Full body shot, sitting on stool.", "Full body shot, leaning against wall."],
        "Cool & Sexy (大胆)": ["Low angle full body shot, sharp gaze.", "Full body shot, sitting on floor.", "Full body shot, back view looking over shoulder.", "Full body shot, lying on luxury sofa."],
        "Cute & Active (動き)": ["Full body shot, jumping slightly.", "Full body shot, twirling around.", "Full body shot, kneeling on carpet.", "Full body shot, crouching and peeking."]
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        src_img = st.file_uploader("1. キャスト写真 (顔の絶対ソース)", type=['png', 'jpg', 'jpeg'])
        ref_img = st.file_uploader("2. 衣装写真 (あればこの服を100%着せる)", type=['png', 'jpg', 'jpeg'])
        st.divider()
        cloth_main = st.selectbox("3. スタイル (参考画像なし時のみ有効)", ["リゾートビキニ", "タイトミニドレス", "清楚ワンピース", "ナース服", "バニーガール", "メイド服", "浴衣"])
        cloth_detail = st.text_input("追加指示", placeholder="例：黒サテン地、ピンクのリボン")
        vibe_choice = st.selectbox("4. Vibe (ポーズ系統)", list(POSE_LIBRARY.keys()))
        bg = st.selectbox("5. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "ビーチ"])
        st.divider()
        run_button = st.button("✨ 4枚一括生成開始")

    if run_button and src_img:
        # 選択したVibeから4つのポーズを抽出
        selected_poses = POSE_LIBRARY[vibe_choice]
        st.subheader(f"🖼️ 生成結果 [{vibe_choice}]")
        
        cols_row1 = st.columns(2)
        cols_row2 = st.columns(2)
        placeholders = [cols_row1[0], cols_row1[1], cols_row2[0], cols_row2[1]]

        base_parts = [types.Part.from_bytes(data=src_img.getvalue(), mime_type='image/jpeg')]
        if ref_img:
            base_parts.append(types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg'))

        # --- ロジック：参考画像優先 & マスターアンカー ---
        if ref_img:
            # 参考画像がある場合は、選択リストを無視して「DNAの移植」を指示
            outfit_logic = f"CLOTHING: Apply the exact colors, patterns, and design DNA from IMAGE 2 onto a professional outfit. {cloth_detail}."
        else:
            outfit_logic = f"CLOTHING: A high-quality {cloth_main}. {cloth_detail}."

        # 1枚目を「アンカー（基準）」にし、4枚を2x2グリッドで同時生成（衣装ズレ防止）
        prompt = (
            f"ABSOLUTE RULE 1: IDENTITY. The woman must be a PERFECT CLONE of IMAGE 1. Face and bone structure are identical. Ignore face in IMAGE 2.\n"
            f"ABSOLUTE RULE 2: CONSISTENCY. This is a 2x2 grid. All 4 panels MUST have the exact same outfit and facial features.\n"
            f"ABSOLUTE RULE 3: MOUTH. Lips sealed, NO TEETH visible in any panel.\n\n"
            f"OUTFIT: {outfit_logic}\n"
            f"POSES: [Top-Left: {selected_poses[0]}], [Top-Right: {selected_poses[1]}], [Bottom-Left: {selected_poses[2]}], [Bottom-Right: {selected_poses[3]}].\n"
            f"ENVIRONMENT: {bg}. Professional 8k photography, sharp focus."
        )

        with st.spinner("キャストの顔と衣装を同期中..."):
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
                    
                    # 2:3比率のまま4分割
                    coords = [(0, 0, w//2, h//2), (w//2, 0, w, h//2), (0, h//2, w//2, h), (w//2, h//2, w, h)]
                    
                    for i, coord in enumerate(coords):
                        with placeholders[i]:
                            cropped = full_img.crop(coord).resize((600, 900))
                            st.image(cropped, use_container_width=True)
                            
                            buf = io.BytesIO()
                            cropped.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p{i+1}.jpg", mime="image/jpeg", key=f"dl_{i}")
                else:
                    st.error("AI規制によりブロックされました。")
            except Exception as e:
                st.error(f"エラー: {e}")

st.markdown("---")
st.caption("© 2026 Karinto Group - Master Identity Engine")
