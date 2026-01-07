import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- 1. 認証機能 (パスワード設定) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 Karinto Group Image Tool")
        pwd = st.text_input("合言葉を入力してください", type="password")
        if st.button("ログイン"):
            if pwd == "karinto": # 好きな合言葉に変更可能
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

    st.title("📸 AI KISEKAE Manager [4-Pose Edition]")

    with st.sidebar:
        st.subheader("⚙️ 生成設定")
        source_img = st.file_uploader("1. 元写真をアップロード", type=['png', 'jpg', 'jpeg'])
        
        # 服装のハイブリッド選択
        cloth_main = st.selectbox("2. 服装の系統", 
            ["清楚ワンピース", "タイトミニドレス", "OL風オフィスカジュアル", 
             "ナース服", "バニーガール", "メイド服", "リゾートビキニ", "浴衣"])
        cloth_detail = st.text_input("詳細指定（色、素材、デザイン）", placeholder="例：黒のサテン地、赤いリボン")
        
        bg = st.selectbox("3. 背景", ["高級ホテル", "夜の繁華街", "撮影スタジオ", "カフェテラス", "ビーチ"])
        
        st.divider()
        run_button = st.button("✨ 4枚同時に生成開始")

    if run_button and source_img:
        # 固定する4つのポーズ
        poses = [
            "Full body shot, standing straight, facing forward.", # 正面
            "Full body shot, posing from a 45-degree angle, hand on hip.", # 斜め
            "Full body shot, sitting gracefully on a chair.", # 座り姿
            "Full body shot, looking back over the shoulder." # 振り返り
        ]
        
        st.subheader("🖼️ 生成結果")
        cols_row1 = st.columns(2)
        cols_row2 = st.columns(2)
        placeholders = [cols_row1[0], cols_row1[1], cols_row2[0], cols_row2[1]]

        for i, pose_text in enumerate(poses):
            with placeholders[i]:
                with st.spinner(f"ポーズ {i+1} を生成中..."):
                    try:
                        # 黄金プロンプト
                        prompt = (
                            f"IMAGE EDITING TASK: Change clothes and background while keeping the face. "
                            f"COMPOSITION: {pose_text} " 
                            f"OUTFIT: A high-quality {cloth_main}. {cloth_detail}. "
                            f"BACKGROUND: {bg} with professional bokeh blur. "
                            f"MOUTH: LIPS SEALED TOGETHER. NO TEETH VISIBLE. " # 歯出し禁止
                            f"FOCUS: Razor-sharp focus on the subject. " # 人物シャープ化
                            f"IDENTITY: Keep the exact facial features of the Japanese woman in the reference." 
                            f"QUALITY: Photorealistic photography, 8k, masterpiece."
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
                            st.image(img, caption=f"ポーズ {i+1}", use_container_width=True)
                            
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG")
                            st.download_button(label=f"保存 {i+1}", data=buf.getvalue(), file_name=f"p{i+1}.jpg", mime="image/jpeg")
                        else:
                            st.error(f"ポーズ {i+1}: 生成失敗")
                    except Exception as e:
                        st.error(f"ポーズ {i+1} エラー: {e}")
                    time.sleep(1) # API負荷軽減

st.markdown("---")
st.caption("© 2026 Karinto Group Professional Tool")
