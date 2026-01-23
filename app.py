import streamlit as st
import logic_kisekae
import logic_flatlay

# --- 1. アプリ全体の基本設定 ---
st.set_page_config(
    page_title="AI KISEKAE Manager Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. サイドバーでメニュー切り替え ---
# ここで選んだものだけが実行されるため、サイドバーが混ざりません
st.sidebar.title("🚀 NAVIGATION")
mode = st.sidebar.radio(
    "機能を選択してください",
    ["✨ AI KISEKAE (Main)", "👕 平置きアンカー生成"],
    index=0
)

st.sidebar.divider() # 区切り線

# --- 3. 選択された機能だけを呼び出す ---
if mode == "✨ AI KISEKAE (Main)":
    # KISEKAE側のサイドバーとメイン画面が表示される
    logic_kisekae.show_kisekae_ui()

elif mode == "👕 平置きアンカー生成":
    # 平置き側のサイドバーとメイン画面が表示される
    logic_flatlay.show_flatlay_ui()
