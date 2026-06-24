from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

from storenotificationcircula.services.llm.schema import CANONICAL_FIELDS, normalize_outputs, parse_json_object

load_dotenv()

MAX_TEXT_LEN = 12000


def _secret(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _prompt(pdf_text: str) -> str:
    fields = "\n".join(f"- {field}" for field in CANONICAL_FIELDS)
    return f"""你是營運通告欄位抽取助手。請從以下 PDF 文字中抽取通告欄位。

只返回一個 JSON object，不要 markdown，不要解釋。JSON keys 必須使用以下欄位：
{fields}

如果欄位不存在，值填空字串。日期請盡量輸出 YYYY-MM-DD。

PDF 文字：
{pdf_text}
"""


def extract_fields(pdf_text: str) -> dict:
    api_key = _secret("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 未配置。")
    model = _secret("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    base_url = _secret("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
    resp = requests.post(
        f"{base_url}/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": _secret("ANTHROPIC_VERSION", "2023-06-01"),
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": int(_secret("ANTHROPIC_MAX_TOKENS", "1500")),
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": _prompt(pdf_text[:MAX_TEXT_LEN]),
                }
            ],
        },
        timeout=90,
    )
    if not resp.ok:
        raise RuntimeError(f"Claude {resp.status_code}：{resp.text}")
    blocks = resp.json().get("content", [])
    text = "\n".join(block.get("text", "") for block in blocks if block.get("type") == "text").strip()
    if not text:
        raise RuntimeError("Claude 未返回可解析文本。")
    return normalize_outputs(parse_json_object(text))
