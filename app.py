import streamlit as st
import logic_kisekae
# logic_flatlay.py がある場合はインポートしてください

# --- 1. 基本設定 (v3.2 黄金律準拠) ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro v3.2",
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
        # 指定のパスワードで認証
        if password_input == "karin10":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Password incorrect")
    return False

# --- 3. メイン処理 (モード切り替え) ---
if check_password():
    # サイドバー最上部の唯一のメニュー（ここで選択権を一元管理）
    # v3.2仕様: ラベルを空にして二重化を防止、名称をシンプルに
    mode = st.sidebar.radio(
        "", 
        ["✨ AI KISEKAE", "👕 洋服制作君"], 
        index=0,
        label_visibility="collapsed"
    )
    st.sidebar.divider()

    # モードに応じたUI呼び出し
    if mode == "✨ AI KISEKAE":
        # 内部で「顔・体型固定」と「カラー上書き」を実行
        logic_kisekae.show_kisekae_ui()
    else:
        st.header("👕 洋服制作君 ver3.2")
        st.info("洋服アンカー制作ロジックをここに展開可能です。")
