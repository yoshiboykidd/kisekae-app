import streamlit as st
import os
import sys

# --- 強制パス設定（決定版） ---
# app.pyがある場所にある 'modules' フォルダを、Pythonの検索リストの最優先（0番目）に追加します
modules_path = os.path.join(os.path.dirname(__file__), "modules")
if modules_path not in sys.path:
    sys.path.insert(0, modules_path)

# --- 1. アプリ全体の基本設定 ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro",
    layout="wide"
)

# --- 2. モジュールのインポート ---
# フォルダ名を介さず、ファイル名を直接指定して読み込みます
try:
    import logic_kisekae
    import logic_flatlay
except Exception as e:
    st.error(f"【エラー】ファイルが読み込めませんでした。GitHubの構成を再確認してください。: {e}")
    st.stop()

# --- 3. 画面構成 ---
st.title("AI KISEKAE Manager")

tab1, tab2 = st.tabs(["✨ AI KISEKAE (Main)", "👕 平置きアンカー生成"])

with tab1:
    # 'modules.' を外して呼び出し
    logic_kisekae.show_kisekae_ui()

with tab2:
    # 'modules.' を外して呼び出し
    logic_flatlay.show_flatlay_ui()
