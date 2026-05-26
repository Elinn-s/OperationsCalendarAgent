"""Quick smoke test: PDF extraction → Dify field extraction."""
import json
import pdfplumber
import requests
from dotenv import load_dotenv
import os

load_dotenv()

PDF_PATH = r"data\H_GO26_001有关：2026年春节期间物料配货安排的通告.pdf"
API_KEY = os.getenv("DIFY_API_KEY")
BASE_URL = os.getenv("DIFY_BASE_URL")


def extract_pdf_text(path: str) -> str:
    import fitz  # pymupdf
    parts = []
    doc = fitz.open(path)
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            parts.append(text)
    doc.close()
    return "\n".join(parts)


def call_dify(pdf_text: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/workflows/run",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={
            "inputs": {"pdf_text": pdf_text},
            "response_mode": "blocking",
            "user": "demo-user",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    print("=== Step 1: Extract PDF text ===")
    text = extract_pdf_text(PDF_PATH)
    print(text[:800])
    print(f"\n[Total chars: {len(text)}]\n")

    print("=== Step 2: Call Dify workflow ===")
    result = call_dify(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
