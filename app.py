import streamlit as st
import os
import sys

# --- 強制パス設定 ---
# 現在の app.py がある場所を特定し、modules フォルダを探せるようにします
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# --- 1. アプリ全体の基本設定 ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro",
    layout="wide"
)

# --- 2. モジュールのインポート ---
try:
    # フォルダ.ファイル名 の形式で直接指定
    import modules.logic_kisekae as logic_kisekae
    import modules.logic_flatlay as logic_flatlay
except Exception as e:
    st.error(f"【エラー】モジュールが読み込めません。GitHubの構成を確認してください。: {e}")
    # どこで探しているかを表示（デバッグ用）
    st.write(f"現在のパス: {sys.path}")
    st.stop()

# --- 3. 画面構成 ---
st.title("AI KISEKAE Manager")

tab1, tab2 = st.tabs(["✨ AI KISEKAE (Main)", "👕 平置きアンカー生成"])

with tab1:
    logic_kisekae.show_kisekae_ui()

with tab2:
    logic_flatlay.show_flatlay_ui()
