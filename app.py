import streamlit as st
import logic_kisekae
import logic_flatlay

st.set_page_config(page_title="AI KISEKAE Manager Pro", layout="wide")

st.title("AI KISEKAE Manager")

# タブの作成
tab1, tab2 = st.tabs(["✨ AI KISEKAE (Main)", "👕 平置きアンカー生成"])

with tab1:
    # この中で呼び出される logic_kisekae 内の st.sidebar は
    # tab1 が選択されている時だけ表示されます
    logic_kisekae.show_kisekae_ui()

with tab2:
    # この中で呼び出される logic_flatlay 内の st.sidebar は
    # tab2 が選択されている時だけ表示されます
    logic_flatlay.show_flatlay_ui()
