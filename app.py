import streamlit as st
import logic_kisekae
import logic_flatlay

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

# --- メイン処理 (v3.0 メニュー一本化) ---
if check_password():
    # ラベルを空にし、表示を消すことで二重化を防止
    mode = st.sidebar.radio(
        "", 
        ["✨ AI KISEKAE", "👕 洋服制作君"], 
        index=0,
        label_visibility="collapsed"
    )
    st.sidebar.divider()

    if mode == "✨ AI KISEKAE":
        logic_kisekae.show_kisekae_ui()
    else:
        # 以前の logic_flatlay を呼び出し
        logic_flatlay.show_flatlay_ui()
