# --- (中略：これまでの認証やポーズロジックは継承) ---

# --- プロンプト掟強化 (ver 2.19: 複合アンカーの固定) ---
if style_part:
    # 参考画像がある場合：画像の内容をテキストで「縛る」
    wardrobe_instruction = (
        f"FIXED WARDROBE ANCHOR: The subject MUST wear the IDENTICAL outfit shown in IMAGE 2.\n"
        f"STRICT DETAILS: {cloth_detail}.\n"
        f"Treat the text details as the EXACT specifications of the outfit in IMAGE 2. Do not change them across shots."
    )
else:
    # 参考画像がない場合：生成したアンカー画像とテキストを同期
    wardrobe_instruction = (
        f"FIXED WARDROBE ANCHOR: The subject MUST wear the EXACT outfit from IMAGE 2 (Session Anchor).\n"
        f"STRICT DETAILS: {cloth_detail}.\n"
        f"Every button, lace, and fabric texture must be 100% consistent with IMAGE 2."
    )

prompt = (
    f"STRICT MANDATE: GENERATE ONE SINGLE PERSON ONLY. NO COLLAGE.\n"
    f"1. BODY ANCHOR (IMAGE 1): Use 100% of the woman's actual physique/mass from IMAGE 1. Discard IMAGE 3's thinness.\n"
    f"2. {wardrobe_instruction}\n"
    f"3. BACKGROUND: {final_bg_prompt}.\n"
    f"4. POSE (IMAGE 3): Skeleton-only guide for '{angle_label}' pose.\n"
    f"5. STYLE: 8k photorealistic, 85mm portrait, Japanese woman, lips sealed."
)
# --- (後略：生成・出力処理) ---
