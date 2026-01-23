import streamlit as st
import logic_kisekae

# --- 1. アプリ全体の基本設定 (ver 2.88 : 復旧版) ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
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

# --- 3. メイン機能の表示 ---
if check_password():
    # 余計なモード選択を廃止し、即座にメインを表示
    logic_kisekae.show_kisekae_ui()
