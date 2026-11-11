"""Gemini image generation shared by the KISEKAE and flat-lay workflows."""
import logging
import re
import time

from google.genai import types

LOGGER = logging.getLogger(__name__)
IMAGE_MODEL = "gemini-3-pro-image"


def _error_code(exc):
    code = getattr(exc, "code", None)
    if callable(code):
        code = code()
    if code is not None:
        match = re.search(r"\b(400|401|402|403|404|429|500|502|503|504)\b", str(code))
        if match:
            return int(match.group(1))
    match = re.search(r"\b(400|401|402|403|404|429|500|502|503|504)\b", str(exc))
    return int(match.group(1)) if match else None


def generate_image(client, contents, prompt, *, aspect_ratio="2:3", max_retries=2, sleep=time.sleep):
    """Return PNG/JPEG bytes on success, otherwise an actionable error string.

    Retry only HTTP 503, up to max_retries additional requests. Never retry
    safety blocks or client/billing/model errors automatically.
    """
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
    )
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=IMAGE_MODEL, contents=[*contents, prompt], config=config
            )
            for candidate in (getattr(response, "candidates", None) or []):
                content = getattr(candidate, "content", None)
                for part in (getattr(content, "parts", None) or []):
                    inline = getattr(part, "inline_data", None)
                    data = getattr(inline, "data", None)
                    if isinstance(data, bytes) and data:
                        return data
                reason = getattr(candidate, "finish_reason", None)
                if reason:
                    LOGGER.warning("Gemini returned no image, finish_reason=%s", reason)
                    return f"画像未生成（finish_reason: {reason}）"
            feedback = getattr(response, "prompt_feedback", None)
            return f"画像未生成（応答に画像データなし。prompt_feedback: {feedback}）"
        except Exception as exc:
            code = _error_code(exc)
            LOGGER.warning("Gemini image attempt %d failed (HTTP %s): %s", attempt + 1, code, exc)
            if code == 503 and attempt < max_retries:
                sleep(2 ** (attempt + 1))
                continue
            if code == 404:
                return "SYSTEM_ERROR (404): モデルが見つかりません。APIキーとモデル利用権限を確認してください。"
            if code in (401, 403):
                return f"SYSTEM_ERROR ({code}): APIキーまたはアクセス権限を確認してください。"
            if code in (402, 429):
                return f"SYSTEM_ERROR ({code}): API利用枠・残高・レート制限を確認してください。"
            if code == 400:
                return f"SYSTEM_ERROR (400): 入力画像・リクエスト形式を確認してください。詳細: {exc}"
            if code == 503:
                return "SYSTEM_ERROR (503): サーバーが混雑しています。2回再試行しましたが失敗しました。"
            return f"SYSTEM_ERROR: {exc}"
    return "SYSTEM_ERROR: 画像生成に失敗しました。"
