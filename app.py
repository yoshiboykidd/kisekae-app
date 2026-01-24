import streamlit as st
import logic_kisekae
import logic_flatlay  # サブ機能を再度読み込みます

# --- 1. 基本設定 (v2.95) ---
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

# --- 3. メイン処理 (モード切り替え) ---
if check_password():
    st.sidebar.title("🚀 MENU")
    mode = st.sidebar.radio(
        "機能を選択してください",
        ["✨ AI KISEKAE (Main)", "👕 洋服アンカー制作 (Sub)"],
        index=0
    )
    st.sidebar.divider()

    if mode == "✨ AI KISEKAE (Main)":
        logic_kisekae.show_kisekae_ui()
    else:
        logic_flatlay.show_flatlay_ui()
