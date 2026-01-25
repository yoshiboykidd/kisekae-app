import streamlit as st
import logic_kisekae
# logic_flatlay がある場合はここに追加

# --- 基本設定 ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- パスワード認証 ---
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

# --- メイン処理 ---
if check_password():
    # サイドバー最上部の唯一のメニュー
    mode = st.sidebar.radio(
        "機能選択", 
        ["✨ AI KISEKAE", "👕 洋服制作君"], 
        index=0,
        label_visibility="collapsed"
    )
    st.sidebar.divider()

    if mode == "✨ AI KISEKAE":
        logic_kisekae.show_kisekae_ui()
    else:
        st.header("👕 洋服制作君 ver3.1")
        st.info("洋服アンカー制作ロジックをここに展開可能です。")
