import streamlit as st
import logic_kisekae
import logic_flatlay
import logic_dx  # 新しく作成するDX版モジュールをインポート

# --- 1. 基本設定 ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro v3.17 DX", # バージョン表記を更新
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

# --- 3. メイン処理 ---
if check_password():
    # サイドバーのメニュー：DX版の選択肢を追加
    mode = st.sidebar.radio(
        "機能選択", 
        ["✨ AI KISEKAE", "👕 洋服制作君", "💎 AI KISEKAE DX"], # DX版を追加
        index=0,
        label_visibility="collapsed" 
    )
    st.sidebar.divider()

    if mode == "✨ AI KISEKAE":
        # 通常の着せ替えロジック (Gemini版)
        logic_kisekae.show_kisekae_ui()
    elif mode == "👕 洋服制作君":
        # 洋服制作ロジック
        logic_flatlay.show_flatlay_ui()
    else:
        # 💎 DX版ロジック (Fal.ai版) を起動
        logic_dx.show_dx_ui()
