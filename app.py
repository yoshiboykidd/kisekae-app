import streamlit as st
import logic_kisekae
import logic_flatlay
import logic_dx  # DX版モジュールの読み込み

# --- 1. 基本設定 ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro v3.17",
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
        # パスワード：karin10
        if password_input == "karin10":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Password incorrect")
    return False

# --- 3. メイン処理 ---
if check_password():
    # DXモードの開放状態を管理 (初期化)
    if "dx_enabled" not in st.session_state:
        st.session_state["dx_enabled"] = False

    # --- サイドバーメニューの構築 ---
    menu_options = ["✨ AI KISEKAE", "👕 洋服制作君"]
    
    # dx10 が入力された場合のみメニューに DX を追加
    if st.session_state["dx_enabled"]:
        menu_options.append("💎 AI KISEKAE DX")

    # 機能選択ラジオボタン
    mode = st.sidebar.radio(
        "機能選択", 
        menu_options, 
        index=0,
        label_visibility="collapsed" 
    )
    
    st.sidebar.divider()

    # --- モードに応じた各ロジックの呼び出し ---
    if mode == "✨ AI KISEKAE":
        # 通常の着せ替え (Gemini版)
        logic_kisekae.show_kisekae_ui()
    elif mode == "👕 洋服制作君":
        # 洋服制作
        logic_flatlay.show_flatlay_ui()
    elif mode == "💎 AI KISEKAE DX":
        # DX版 (Fal.ai版)
        logic_dx.show_dx_ui()

    # --- 隠し要素のトリガーエリア ---
    # サイドバーの最下部に配置
    with st.sidebar:
        st.write("") # スペース確保
        # ラベルなしの入力欄
        unlock_key = st.text_input("Admin Access", type="password", key="dx_unlock", label_visibility="collapsed")
        
        # 修正ポイント：まだ有効化されていない時だけ rerun を実行してループを防ぐ
        if unlock_key == "dx10" and not st.session_state["dx_enabled"]:
            st.session_state["dx_enabled"] = True
            st.rerun()
