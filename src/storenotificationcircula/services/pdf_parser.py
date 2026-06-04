import fitz  # PyMuPDF
import numpy as np
import cv2
import gc
from pathlib import Path

_engine = None
_RENDER_SCALE = 1.35


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR()
    return _engine


def _page_to_image(page: fitz.Page) -> np.ndarray:
    mat = fitz.Matrix(_RENDER_SCALE, _RENDER_SCALE)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def extract_text(pdf_path: str | Path) -> str:
    engine = _get_engine()
    pages = []
    doc = fitz.open(str(pdf_path))
    try:
        for page in doc:
            img = _page_to_image(page)
            try:
                result, _ = engine(img)
                lines = [item[1] for item in result if item[1].strip()] if result else []
                pages.append("\n".join(lines))
            finally:
                del img
                gc.collect()
    finally:
        doc.close()

    text = "\n\n".join(pages)
    if not text.strip():
        raise ValueError("OCR 未识别到任何文字，请检查 PDF 是否可读")
    return text
