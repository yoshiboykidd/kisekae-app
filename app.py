import streamlit as st
import os

# --- 1. アプリ全体の基本設定 ---
# 注: st.set_page_config はアプリ内で最初に一度だけ呼び出す必要があります
st.set_page_config(
    page_title="AI KISEKAE Manager Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. モジュールのインポート ---
# modules フォルダからそれぞれのロジックを読み込みます
try:
    # 標準的なパッケージインポート
    from modules import logic_kisekae
    from modules import logic_flatlay
except ImportError:
    # 環境によって上記が失敗する場合の代替インポート
    import modules.logic_kisekae as logic_kisekae
    import modules.logic_flatlay as logic_flatlay

# --- 3. 画面構成 ---
st.title("AI KISEKAE Manager")

# タブで機能を分離（見た目と中身を一致させます）
tab1, tab2 = st.tabs(["✨ AI KISEKAE (Main)", "👕 平置きアンカー生成"])

with tab1:
    # modules/logic_kisekae.py のメイン関数を実行
    logic_kisekae.show_kisekae_ui()

with tab2:
    # modules/logic_flatlay.py のメイン関数を実行
    logic_flatlay.show_flatlay_ui()
