import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time
import random

# --- 1. 認証機能 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 Karinto Group Image Tool")
        pwd = st.text_input("合言葉を入力してください", type="password")
        if st.button("ログイン"):
            if pwd == "karinto": 
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

    st.title("📸 AI KISEKAE Manager [Vibe & Random Pose]")

    # --- ポーズ・ライブラリ (Vibeごとに定義) ---
    POSE_LIBRARY = {
        "Standard (王道)": [
            "Full body shot, standing straight, facing forward.",
            "Full body shot, posing from a 45-degree angle, hand on hip.",
            "Full body shot, sitting gracefully on a chair.",
            "Full body shot, looking back over the shoulder.",
            "Full body shot, leaning slightly forward with a natural smile.",
            "Full body shot, standing with legs crossed elegantly.",
            "Full body shot, sitting on the floor with legs tucked.",
            "Full body shot, walking toward the camera naturally."
        ],
        "Cool & Elegant (綺麗め)": [
            "Full body shot, leaning against a wall with a cool expression.",
            "Full body shot, arms crossed, looking at the camera with sharp eyes.",
            "Full body shot, sitting on a high stool with one leg extended.",
            "Full body shot, adjusting hair with one hand, looking away.",
            "Full body shot, hand in pocket, standing with a confident posture.",
            "Full body shot, professional model pose, highlighting the body line.",
            "Full body shot, walking away and looking back sharply.",
            "Full body shot, sitting in a luxury sofa, looking dignified."
        ],
        "Cute & Sweet (可愛い)": [
            "Full body shot, hands on cheeks, tilted head, cute expression.",
            "Full body shot, playing with hair, looking shy but charming.",
            "Full body shot, sitting with knees hugged, looking up at the camera.",
            "Full body shot, blowing a small kiss or waving hand gently.",
            "Full body shot, holding a small accessory, bright and airy mood.",
            "Full body shot, spinning slowly, skirt fluttering slightly.",
            "Full body shot, sitting on the edge of a bed, soft and sweet pose.",
            "Full body shot, peeking from behind a door or curtain."
        ]
    }

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. 元写真をアップロード", type=['png', 'jpg', 'jpeg'])
        
        cloth_main = st.selectbox("2. 服装の系統", ["清楚ワンピース", "タイトミニドレス", "ナース服", "バニーガール", "メイド服", "リゾートビキニ", "浴衣"])
        cloth_detail = st.text_input("詳細指定（色、素材など）", placeholder="例：黒のサテン地、赤いリボン")
        
        # Vibeの選択
        vibe_choice = st.selectbox("3. ポーズの雰囲気 (Vibe)", list(POSE_LIBRARY.keys()))
        
        bg = st.selectbox("4. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "ビーチ"])
        
        st.divider()
        run_button = st.button("✨ 4枚一括生成（ポーズはランダム）")

    if run_button and source_img:
        # 選択されたVibeからランダムに4つ抽出
        selected_poses = random.sample(POSE_LIBRARY[vibe_choice], 4)
        
        st.subheader(f"🖼️ 生成結果 [{vibe_choice}]")
        cols_row1 = st.columns(2)
        cols_row2 = st.columns(2)
        placeholders = [cols_row1[0], cols_row1[1], cols_row2[0], cols_row2[1]]

        for i, pose_text in enumerate(selected_poses):
            with placeholders[i]:
                with st.spinner(f"デザイン {i+1} を生成中..."):
                    try:
                        # 不変の黄金ルールを統合したプロンプト
                        prompt = (
                            f"IMAGE EDITING TASK: Change clothes and background while keeping the face. "
                            f"COMPOSITION: {pose_text} " 
                            f"OUTFIT: A high-quality {cloth_main}. {cloth_detail}. "
                            f"BACKGROUND: {bg} with professional bokeh blur. "
                            f"MOUTH (STRICT): LIPS MUST BE SEALED TOGETHER. NO TEETH VISIBLE. " # 歯出し禁止
                            f"FOCUS: Razor-sharp focus on the entire person. No blur on the subject. " # 人物シャープ化
                            f"IDENTITY: Keep the exact facial features and bone structure of the Japanese woman in the reference." 
                            f"QUALITY: Photorealistic photography, 8k, professional studio lighting, masterpiece."
                        )

                        response = client.models.generate_content(
                            model='gemini-3-pro-image-preview',
                            contents=[types.Part.from_bytes(data=source_img.getvalue(), mime_type='image/jpeg'), prompt],
                            config=types.GenerateContentConfig(
                                response_modalities=['IMAGE'],
                                safety_settings=[types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE')],
                                image_config=types.ImageConfig(aspect_ratio="2:3")
                            )
                        )

                        if response.candidates and response.candidates[0].content.parts:
                            img_data = response.candidates[0].content.parts[0].inline_data.data
                            img = Image.open(io.BytesIO(img_data)).resize((600, 900))
                            st.image(img, use_container_width=True)
                            
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"pose_{i+1}.jpg", mime="image/jpeg")
                        else:
                            st.error(f"生成失敗: フィルター制限")
                    except Exception as e:
                        st.error(f"エラー: {e}")
                    time.sleep(1)

st.markdown("---")
st.caption("© 2026 Karinto Group - Antigravity Powered Tool")
