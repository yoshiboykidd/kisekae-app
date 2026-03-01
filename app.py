import streamlit as st
import logic_kisekae
import logic_flatlay
import logic_dx  # ファイルは存在している前提

# --- 1. 基本設定 ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro v3.17", # 表向きは通常のバージョン表記
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
    # DXモードの開放状態を管理
    if "dx_enabled" not in st.session_state:
        st.session_state["dx_enabled"] = False

    # 基本のメニュー
    menu_options = ["✨ AI KISEKAE", "👕 洋服制作君"]
    
    # 隠しフラグが立っている場合のみ DX を追加
    if st.session_state["dx_enabled"]:
        menu_options.append("💎 AI KISEKAE DX")

    mode = st.sidebar.radio(
        "機能選択", 
        menu_options, 
        index=0,
        label_visibility="collapsed" 
    )
    
    st.sidebar.divider()

    # --- 隠し要素のトリガー ---
    # サイドバーの最下部に、ラベルのない小さな入力欄を配置
    with st.sidebar:
        st.write("") # スペース確保
        # 非常に目立たない形で配置。知っている人だけが入力する
        unlock_key = st.text_input("Admin Access", type="password", key="dx_unlock", label_visibility="collapsed")
        if unlock_key == "dx10": # 隠しコマンド
            st.session_state["dx_enabled"] = True
            st.rerun()

    # モードに応じた画面表示
    if mode == "✨ AI KISEKAE":
        logic_kisekae.show_kisekae_ui()
    elif mode == "👕 洋服制作君":
        logic_flatlay.show_flatlay_ui()
    elif mode == "💎 AI KISEKAE DX":
        logic_dx.show_dx_ui()
