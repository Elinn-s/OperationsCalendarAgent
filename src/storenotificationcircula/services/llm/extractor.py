from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _provider() -> str:
    return os.getenv("LLM_PROVIDER", "dify").strip().lower()


def extract_fields(pdf_text: str) -> dict:
    provider = _provider()
    if provider in {"claude", "anthropic"}:
        from storenotificationcircula.services.llm.claude_client import extract_fields as extract_with_claude

        return extract_with_claude(pdf_text)
    if provider == "dify":
        from storenotificationcircula.services.llm.dify_client import extract_fields as extract_with_dify

        return extract_with_dify(pdf_text)
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")
