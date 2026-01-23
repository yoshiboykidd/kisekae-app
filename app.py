import streamlit as st

# 全体設定
st.set_page_config(page_title="Image Manager Pro", layout="wide")

# パスワード認証（略）
def check_password():
    # ...認証処理...
    return True

if check_password():
    st.sidebar.title("MENU")
    mode = st.sidebar.radio("機能選択", ["メイン機能", "サブ機能"])

    if mode == "メイン機能":
        try:
            # 使う直前に読み込むことで、サブ機能のエラーに巻き込まれないようにする
            import logic_kisekae
            logic_kisekae.show_kisekae_ui()
        except Exception as e:
            st.error(f"メイン機能の読み込みに失敗しました: {e}")

    elif mode == "サブ機能":
        try:
            import logic_flatlay
            logic_flatlay.show_flatlay_ui()
        except Exception as e:
            st.error(f"サブ機能の読み込みに失敗しました: {e}")
