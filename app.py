import streamlit as st

# ==========================================================
# 1. システム設定：AI KISEKAE Manager ver 2.43
# ==========================================================
st.set_page_config(page_title="AI KISEKAE Manager v2.43", layout="wide")

# カスタムCSSでUIをプロ仕様に
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #ff4b4b; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("👗 AI KISEKAE Manager <span style='font-size:0.6em;'>ver 2.43</span>", unsafe_allow_html=True)
st.sidebar.header("🛠 Control Panel")

# ==========================================================
# 2. 黄金律定義：2.43 固定パラメータ (最優先指示)
# ==========================================================
# このプロンプトがすべての生成の核となり、顔と体型を固定します
FIXED_IDENTITY_243 = (
    "Masterpiece, photorealistic Japanese female, Version 2.43 fixed identity. "
    "Specific facial features of 2.43, natural and consistent skin texture, "
    "ideal body proportions of 2.43. Character consistency is top priority."
)

# ==========================================================
# 3. 修正版：6つのセーフ・カテゴリー
# ==========================================================
CATEGORIES = {
    "1. 私服（日常）": {"en": "Casual everyday Japanese fashion", "env": "Natural daylight, street or cafe"},
    "2. 水着（ビーチ）": {"en": "High-end stylish beachwear", "env": "Sunny resort, poolside"},
    "3. 部屋着（リラックス）": {"en": "Soft lounge wear, silk or knit lingerie-style", "env": "Cozy bedroom, warm dim lighting"},
    "4. オフィス（スーツ）": {"en": "Elegant business professional", "env": "Modern office, clean lighting"},
    "5. コスチューム": {"en": "High-quality themed costume", "env": "Studio setup, concept background"},
    "6. 夜の装い（ドレス）": {"en": "Sophisticated evening gown", "env": "Luxury lounge, night city bokeh"}
}

# ==========================================================
# 4. ユーザーインターフェース
# ==========================================================
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. 衣装の方向性")
    selected_cat = st.selectbox("カテゴリー選択", list(CATEGORIES.keys()))
    
    st.subheader("2. 参考画像のアップロード")
    ref_image = st.file_uploader("衣装の参考にしたい画像をアップ（任意）", type=['png', 'jpg', 'jpeg'])

with col2:
    st.subheader("3. 衣装仕様書（詳細指示）")
    spec_sheet = st.text_area(
        "具体的な色や素材、形状のこだわりを入力", 
        placeholder="例：色はパステルブルー、肩出しのオフショル、膝上のフレアスカート、素材はレース多めで",
        height=200
    )

# ==========================================================
# 5. プロンプト構築エンジン (nanobananaPRO 最適化)
# ==========================================================
def build_manager_prompt(cat_key, specs, has_img):
    cat = CATEGORIES[cat_key]
    
    # 2.43の固定コアを基軸にする
    prompt = f"[IDENTITY_FIX: {FIXED_IDENTITY_243}] "
    
    # カテゴリーと環境のセット
    prompt += f"Clothing Category: {cat['en']}. Lighting & Environment: {cat['env']}. "

    if has_img:
        # 画像がある場合は「2.43への着せ替え」を強調
        prompt += (
            f"Action: Dress the 2.43 character in the outfit from the reference image. "
            f"Modification per Specs: {specs}. "
            f"Ensure the face and body of 2.43 are perfectly preserved."
        )
    else:
        # 仕様書のみの場合は「2.43に似合うデザインの構築」を強調
        prompt += f"Action: Design a high-fashion outfit for 2.43 based on these specs: {specs}. "
    
    prompt += " (extremely detailed, 8k resolution, sharp focus, high quality skin render)"
    return prompt

# ==========================================================
# 6. 実行プロセス
# ==========================================================
if st.button("✨ 画像生成プロンプトを発行"):
    if not spec_sheet and not ref_image:
        st.error("仕様書または参考画像のどちらかは必須です。")
    else:
        final_output_prompt = build_manager_prompt(selected_cat, spec_sheet, ref_image is not None)
        
        st.success("2.43 固定プロンプトの生成が完了しました")
        with st.expander("詳細な送信プロンプトを表示"):
            st.code(final_output_prompt)
        
        # --- ここにnanobananaPRO(Gemini 3 Pro)のAPI連携ロジックを挿入 ---
        st.info("※ API連携により、ここに生成画像が表示されます。")
