import streamlit as st
import logic_kisekae
import logic_flatlay

# --- 1. アプリ全体の基本設定 (ver 2.80) ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro v2.80",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. パスワード認証ロジック ---
def check_password():
    """パスワードが正しいか確認し、成功ならTrue、失敗ならFalseを返す"""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # すでに認証済みの場合はそのまま進む
    if st.session_state["password_correct"]:
        return True

    # ログイン画面の表示
    st.title("🔐 AI KISEKAE Authentication")
    
    # テキストボックスに入力があった際に自動的にボタンが押されたような挙動にする
    password_input = st.text_input("Enter Password", type="password")
    
    if st.button("Login"):
        if password_input == "karin10":
            st.session_state["password_correct"] = True
            st.rerun()  # 画面を即座にメイン機能へ切り替える
        else:
            st.error("😕 Password incorrect")
    
    return False

# --- 3. メイン処理 (認証成功時のみ実行) ---
if check_password():
    # サイドバー：ナビゲーション
    st.sidebar.title(f"🚀 NAVIGATION (v2.80)")
    
    mode = st.sidebar.radio(
        "機能を選択してください",
        ["✨ AI KISEKAE (Main)", "👕 平置きアンカー生成"],
        index=0
    )
    
    st.sidebar.divider()
    
    # 選択されたモードに応じて各ロジックファイルを呼び出し
    if mode == "✨ AI KISEKAE (Main)":
        # logic_kisekae.py 内の関数を呼び出し
        logic_kisekae.show_kisekae_ui()

    elif mode == "👕 平置きアンカー生成":
        # logic_flatlay.py 内の関数を呼び出し
        logic_flatlay.show_flatlay_ui()
