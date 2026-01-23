import streamlit as st
# logic_flatlay は読み込まず、メインのみに集中させます
import logic_kisekae

# --- 1. 基本設定 (v2.90) ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro",
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

# --- 3. メイン機能呼び出し ---
if check_password():
    logic_kisekae.show_kisekae_ui()
