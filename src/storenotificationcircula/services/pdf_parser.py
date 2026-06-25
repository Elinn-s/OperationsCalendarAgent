import os
from pathlib import Path

import fitz  # PyMuPDF


def _local_ocr_enabled() -> bool:
    return os.getenv("ENABLE_LOCAL_OCR", "false").strip().lower() in {"1", "true", "yes", "on"}


def _extract_text_layer(pdf_path: str | Path) -> str:
    pages: list[str] = []
    doc = fitz.open(str(pdf_path))
    try:
        for page in doc:
            pages.append(page.get_text("text").strip())
    finally:
        doc.close()
    return "\n\n".join(page for page in pages if page)


def extract_text(pdf_path: str | Path) -> str:
    text = _extract_text_layer(pdf_path)
    if text.strip():
        return text

    if not _local_ocr_enabled():
        raise ValueError("线上环境未开启本地 OCR。扫描版 PDF 请使用 Plan B 本地 OCR 启动方式识别。")

    try:
        from storenotificationcircula.services.local_ocr.pdf_parser import extract_text_with_ocr
    except Exception as exc:  # pragma: no cover - env dependent
        raise RuntimeError(
            "本地 OCR 依赖未安装。请安装可选依赖 local-ocr 后重试，"
            "例如：uv sync --extra local-ocr"
        ) from exc

    return extract_text_with_ocr(pdf_path)
