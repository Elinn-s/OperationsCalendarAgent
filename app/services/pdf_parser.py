import fitz  # PyMuPDF
import numpy as np
import cv2
from pathlib import Path

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR()
    return _engine


def _pdf_to_images(pdf_path: str | Path) -> list[np.ndarray]:
    doc = fitz.open(str(pdf_path))
    images = []
    for page in doc:
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        images.append(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    doc.close()
    return images


def extract_text(pdf_path: str | Path) -> str:
    images = _pdf_to_images(pdf_path)
    engine = _get_engine()
    pages = []
    for img in images:
        result, _ = engine(img)
        lines = [item[1] for item in result if item[1].strip()] if result else []
        pages.append("\n".join(lines))
    text = "\n\n".join(pages)
    if not text.strip():
        raise ValueError("OCR 未识别到任何文字，请检查 PDF 是否可读")
    return text
