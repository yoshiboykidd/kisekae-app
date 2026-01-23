import streamlit as st
import logic_kisekae

# --- ver 2.89: 復旧最優先構成 ---
st.set_page_config(
    page_title="AI KISEKAE Manager",
    layout="wide"
)

# 認証
if "password_correct" not in st.session_state:
    st.session_state.password_correct = False

if not st.session_state.password_correct:
    st.title("🔐 Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == "karin10":
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Invalid password")
else:
    # メイン機能のみを起動
    logic_kisekae.show_kisekae_ui()
