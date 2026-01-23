import streamlit as st
import logic_kisekae
import logic_flatlay

# --- 1. アプリ全体の基本設定 ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. パスワード認証ロジック (Secrets参照・安全版) ---
def check_password():
    """Secretsからパスワードを読み込み、認証を行う"""
    
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🔐 Authentication")
    password_input = st.text_input("Enter Password", type="password")
    
    if st.button("Login"):
        # ソースコードにパスワードを書かず、Secretsから比較します
        if password_input == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Password incorrect")
    
    return False

# --- 3. メイン処理 ---
if check_password():
    st.sidebar.title("🚀 NAVIGATION")
    mode = st.sidebar.radio(
        "機能を選択してください",
        ["✨ AI KISEKAE (Main)", "👕 平置きアンカー生成"],
        index=0
    )
    
    st.sidebar.divider()

    if mode == "✨ AI KISEKAE (Main)":
        logic_kisekae.show_kisekae_ui()

    elif mode == "👕 平置きアンカー生成":
        logic_flatlay.show_flatlay_ui()
