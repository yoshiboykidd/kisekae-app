import streamlit as st
import logic_kisekae
import logic_flatlay

# --- 1. アプリ全体の基本設定 ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. パスワード認証ロジック ---
def check_password():
    """パスワードが正しいかチェックし、結果を返す"""
    def password_entered():
        if st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # セッションからパスワードを削除
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 初回訪問時
        st.text_input(
            "Enter Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # パスワードが間違っている場合
        st.text_input(
            "Enter Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # パスワードが正しい場合
        return True

# --- 3. メイン処理 ---
if check_password():
    # パスワードが通った後だけ、以下のナビゲーションと機能が表示される
    
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
