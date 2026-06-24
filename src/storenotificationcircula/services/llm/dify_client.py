from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

from storenotificationcircula.services.llm.schema import normalize_outputs

load_dotenv()

MAX_TEXT_LEN = 4000


def _secret(key: str) -> str:
    return os.getenv(key, "")


def _get_api_key() -> str:
    return _secret("DIFY_API_KEY")


def _get_base_url() -> str:
    return (_secret("DIFY_BASE_URL") or _secret("DIFY_API_URL")).rstrip("/")


def extract_fields(pdf_text: str) -> dict:
    if not _get_api_key() or not _get_base_url():
        raise RuntimeError("DIFY_API_KEY / DIFY_BASE_URL 未配置。")
    truncated = pdf_text[:MAX_TEXT_LEN]
    resp = requests.post(
        f"{_get_base_url()}/workflows/run",
        headers={
            "Authorization": f"Bearer {_get_api_key()}",
            "Content-Type": "application/json",
        },
        json={
            "inputs": {"pdf_text": truncated},
            "response_mode": "blocking",
            "user": "demo-user",
        },
        timeout=90,
    )
    if not resp.ok:
        raise RuntimeError(f"Dify {resp.status_code}：{resp.text}")
    outputs = resp.json().get("data", {}).get("outputs", {})
    return normalize_outputs(outputs)
