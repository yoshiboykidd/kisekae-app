import streamlit as st
import logic_kisekae
import logic_flatlay

# --- 1. アプリ全体の基本設定 ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. パスワード認証ロジック (確実なリフレッシュ版) ---
def check_password():
    """パスワードをチェックし、成功したら画面を即座に更新する"""
    
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # すでに認証済みの場合はTrueを返す
    if st.session_state["password_correct"]:
        return True

    # ログイン画面の表示
    st.title("🔐 Authentication")
    password_input = st.text_input("Enter Password", type="password")
    
    if st.button("Login"):
        if password_input == "karin10":
            st.session_state["password_correct"] = True
            st.rerun()  # ★ここが重要：画面を強制的に書き換える
        else:
            st.error("😕 Password incorrect")
    
    return False

# --- 3. メイン処理 ---
if check_password():
    # パスワードが正しい場合のみ、以下のUIが表示される
    
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
