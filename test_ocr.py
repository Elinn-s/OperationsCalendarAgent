"""快速诊断：PDF → 图片 → rapidocr，打印原始结果"""
import fitz
import numpy as np
import cv2
from rapidocr_onnxruntime import RapidOCR

PDF = r"data\H_GO26_001有关：2026年春节期间物料配货安排的通告.pdf"

print("=== Step 1: PDF → 图片 ===")
doc = fitz.open(PDF)
page = doc[0]
mat = fitz.Matrix(2.0, 2.0)
pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
doc.close()
print(f"图片尺寸: {img_bgr.shape}  dtype: {img_bgr.dtype}")

print("\n=== Step 2: RapidOCR ===")
engine = RapidOCR()
result, _ = engine(img_bgr)
print(f"result 类型: {type(result)}")
print(f"result 值:   {result}")

if result:
    print(f"\n识别到 {len(result)} 个文本块，前5条：")
    for item in result[:5]:
        print(item)
