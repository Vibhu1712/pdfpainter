"""OCR a page whose text is drawn as outlines or scanned, with no native PDF engine involved.

    pip install rapidocr onnxruntime      # or: pip install pytesseract  (+ the Tesseract program)
    python examples/ocr_page.py payslip.pdf

Word boxes come back in PDF points, top-left origin, the same space pdfsieve uses, so OCR words
and text-layer words can be mixed freely.
"""

import sys

import pdfpainter
import pdfsieve

DPI = 300
zoom = DPI / 72

with pdfsieve.open(sys.argv[1]) as doc:
    page = doc.page(int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 0)
    img = pdfpainter.render(page, zoom)

words = []
try:
    from rapidocr import RapidOCR
    import numpy as np

    result = RapidOCR()(np.asarray(img))
    for quad, text in zip(result.boxes, result.txts):
        xs, ys = [p[0] for p in quad], [p[1] for p in quad]
        words.append((min(xs) / zoom, min(ys) / zoom, max(xs) / zoom, max(ys) / zoom, text))
except ImportError:
    import pytesseract

    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    for i, text in enumerate(data["text"]):
        if text.strip() and float(data["conf"][i]) >= 30:
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            words.append((x / zoom, y / zoom, (x + w) / zoom, (y + h) / zoom, text))

for x0, y0, x1, y1, text in words:
    print(f"{x0:7.1f} {y0:7.1f} {x1:7.1f} {y1:7.1f}  {text}")
