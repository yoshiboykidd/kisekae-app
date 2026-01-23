import streamlit as st
# 同じ階層（ルート）にあるファイルを直接インポート
import logic_kisekae
import logic_flatlay

# --- 1. アプリ全体の基本設定 ---
# 注: st.set_page_config はアプリ内で最初に一度だけ呼び出す必要があります
st.set_page_config(
    page_title="AI KISEKAE Manager Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 画面構成 ---
st.title("AI KISEKAE Manager")

# タブで機能を分離
# タブをクリックするだけで、中身のプログラムが切り替わります
tab1, tab2 = st.tabs(["✨ AI KISEKAE (Main)", "👕 平置きアンカー生成"])

with tab1:
    # logic_kisekae.py の中にある show_kisekae_ui 関数を実行
    logic_kisekae.show_kisekae_ui()

with tab2:
    # logic_flatlay.py の中にある show_flatlay_ui 関数を実行
    logic_flatlay.show_flatlay_ui()
