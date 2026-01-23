import streamlit as st
import sys
import os

# modules フォルダを読み込めるようにパスを追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

# 自作モジュールのインポート
from modules import logic_kisekae
from modules import logic_flatlay

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
tab1, tab2 = st.tabs(["✨ AI KISEKAE (Main)", "👕 平置きアンカー生成"])

with tab1:
    # modules/logic_kisekae.py の UI を呼び出す
    logic_kisekae.show_kisekae_ui()

with tab2:
    # modules/logic_flatlay.py の UI を呼び出す
    logic_flatlay.show_flatlay_ui()
