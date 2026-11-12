"""Paint a page and outline every word pdfsieve found on it: a quick visual check of positions.

    python examples/word_boxes.py sample.pdf boxes.png
"""

import sys

from PIL import ImageDraw

import pdfpainter
import pdfsieve

src, dst = sys.argv[1], sys.argv[2]
zoom = 2.0
with pdfsieve.open(src) as doc:
    page = doc.page(0)
    img = pdfpainter.render(page, zoom)
    draw = ImageDraw.Draw(img)
    for w in page.words():
        draw.rectangle([v * zoom for v in w[:4]], outline=(230, 40, 40), width=2)
img.save(dst)
print("wrote", dst)
