import streamlit as st
import fal_client
from google import genai
from google.genai import types
import io, requests, random, os
from PIL import Image

# --- 1. 定義データ (日本人女性・実写特化) ---
HAIR_STYLES = {"元画像のまま": "original hairstyle", "ゆるふあ巻き": "soft wavy curls", "ハーフアップ": "half-up", "ツインテール": "twin tails", "ポニーテール": "ponytail", "まとめ髪": "updo", "ストレート": "straight hair"}
HAIR_COLORS = {"元画像のまま": "original hair color", "ナチュラルブラック": "black hair", "ダークブラウン": "dark brown hair", "ashベージュ": "ash beige", "ミルクティーグレージュ": "greige", "ピンクブラウン": "pink brown", "ハニーブロンド": "honey blonde"}

# --- 2. プロンプトエンジン (衣装の馴染ませ・実写化) ---
def get_final_dx_prompt(anchor_text, hair_s, hair_c):
    """
    Inpainting(Fill)用のプロンプト。
    ベースの体型は変えず、指定された衣装だけを実写として馴染ませる。
    """
    security_lock = (
        "High-fidelity clothing integration. Realistic fabric texture. "
        "The subject is a Japanese woman wearing a high-quality outfit. "
        "NO transparency, solid fabric, opaque material. Completely clothed. "
    )
    render_recipe = (
        "Hyper-realistic photography, 8k photo, Sony A7R IV, 35mm lens, f/2.8, "
        "highly detailed skin texture, cinematic lighting, film grain."
    )
    # 髪型と髪色も衣装と一緒に馴染ませる
    return f"{security_lock} WARDROBE: {anchor_text}. HAIR: {hair_s}, Color: {hair_c}. {render_recipe}"

# --- 3. UI メイン処理 ---
def show_dx_ui():
    if "GEMINI_API_KEY" not in st.secrets or "FAL_KEY" not in st.secrets:
        st.error("🔑 APIキーが Secrets に設定されていません。")
        st.stop()
    
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

    if "dx_images" not in st.session_state: st.session_state.dx_images = [None] * 4
    if "dx_anchor" not in st.session_state: st.session_state.dx_anchor = ""
    if "dx_error" not in st.session_state: st.session_state.dx_error = None

    st.header("💎 AI KISEKAE DX v3.25 (Auto-Mask Fill)")
    st.caption("【DX仕様】キャストの体型を維持し、衣装だけを自動認識して着せ替えます")

    # エラー表示エリア (リロードで消さない)
    if st.session_state.dx_error:
        st.error(f"❌ エラーが発生しました:\n\n{st.session_state.dx_error}")
        if st.button("エラー表示を消す"):
            st.session_state.dx_error = None
            st.rerun()

    with st.sidebar:
        st.subheader("🖼️ 画像ソース")
        src_img = st.file_uploader("キャスト (IMAGE 1)", type=['png', 'jpg', 'jpeg'], key="dx_s")
        ref_img = st.file_uploader("衣装 (IMAGE 2)", type=['png', 'jpg', 'jpeg'], key="dx_r")
        
        st.divider()
        st.subheader("💇 スタイル設定")
        hair_s = st.selectbox("髪型", list(HAIR_STYLES.keys()), key="dx_hs")
        hair_c = st.selectbox("🎨 髪色", list(HAIR_COLORS.keys()), key="dx_hc")
        cloth_note = st.text_input("衣装の追加補足", placeholder="例: black satin, lace")
        
        st.divider()
        st.subheader("⚙️ 調整")
        # Inpaintingでは Guidance Scale を上げすぎると「体型」が壊れるため、4.0前後を推奨
        g_scale = st.slider("命令遵守度 (Guidance)", 1.0, 10.0, 4.0)
        steps = st.slider("描き込み回数 (Steps)", 20, 50, 30)
        
        run_btn = st.button("🚀 DX鉄壁一括生成", type="primary")

    if st.session_state.dx_anchor:
        with st.expander("📝 解析された衣装アンカー"):
            st.code(st.session_state.dx_anchor)

    if run_btn and src_img and ref_img:
        st.session_state.dx_images = [None] * 4
        st.session_state.dx_error = None
        status = st.empty(); progress = st.progress(0)
        
        try:
            # Step 1: Geminiによる衣装解析
            status.info("🕒 Step 1/2: 衣装のデザインを解析中...")
            ref_part = types.Part.from_bytes(data=ref_img.getvalue(), mime_type='image/jpeg')
            analysis_p = f"Analyze clothing in keywords ONLY. Focus on material and cut. {cloth_note}"
            response = client.models.generate_content(model='gemini-2.0-flash', contents=[ref_part, analysis_p])
            st.session_state.dx_anchor = response.text.replace("\n", ", ")

            # Step 2: Fal.ai Flux-Fill による着せ替え
            status.info("⏳ Step 2/2: Fal.ai 描画エンジンを起動...")
            src_bytes = src_img.getvalue()
            src_url = fal_client.upload(src_bytes, "image/jpeg")
            
            for i in range(4):
                status.info(f"🎨 着せ替え中 ({i+1}/4)...")
                final_p = get_final_dx_prompt(st.session_state.dx_anchor, HAIR_STYLES[hair_s], HAIR_COLORS[hair_c])
                
                try:
                    # 正しいモデルID: fal-ai/flux-pro/v1/fill
                    result = fal_client.subscribe(
                        "fal-ai/flux-pro/v1/fill",
                        arguments={
                            "image_url": src_url,
                            "prompt": final_p,
                            "mask_prompt": "clothing, dress, outfit, garment", # 服だけを自動認識
                            "num_inference_steps": steps,
                            "guidance_scale": g_scale,
                            "enable_safety_checker": False # 検閲オフ
                        }
                    )
                    image_url = result['images'][0]['url']
                    st.session_state.dx_images[i] = Image.open(requests.get(image_url, stream=True).raw)
                except Exception as inner_e:
                    # エラー詳細を保存
                    st.session_state.dx_error = f"APIエラー: {str(inner_e)}"
                    break
                progress.progress((i+1)/4)
            
            status.empty()
            if not st.session_state.dx_error:
                st.rerun()

        except Exception as e:
            st.session_state.dx_error = f"システムエラー: {str(e)}"
            st.rerun()

    # 表示エリア
    if any(img is not None for img in st.session_state.dx_images):
        cols = st.columns(2)
        for i in range(4):
            with cols[i % 2]:
                if st.session_state.dx_images[i]:
                    st.image(st.session_state.dx_images[i], use_container_width=True)
                    buf = io.BytesIO(); st.session_state.dx_images[i].save(buf, format="JPEG")
                    st.download_button("💾 保存", buf.getvalue(), f"dx_{i}.jpg", key=f"dl_{i}")
