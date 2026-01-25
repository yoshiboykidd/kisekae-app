import streamlit as st
import logic_kisekae
import logic_flatlay  # 先ほど作成したファイルをインポート

# --- 1. 基本設定 ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro v3.1",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. パスワード認証 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.title("🔐 AI KISEKAE Authentication")
    password_input = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        if password_input == "karin10":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Password incorrect")
    return False

# --- 3. メイン処理 ---
if check_password():
    # サイドバーのメニュー：ここで全ての切り替えを管理します
    mode = st.sidebar.radio(
        "機能選択", 
        ["✨ AI KISEKAE", "👕 洋服制作君"], 
        index=0,
        label_visibility="collapsed" # ラベルを隠してUIをスッキリさせます
    )
    st.sidebar.divider()

    if mode == "✨ AI KISEKAE":
        # 着せ替えロジックを起動
        logic_kisekae.show_kisekae_ui()
    else:
        # 洋服制作ロジックを起動（ここが仮置きから本番コードに変わりました）
        logic_flatlay.show_flatlay_ui()
