"""pdfpainter: paint PDF pages to images with Pillow alone, no native PDF engine needed.

Built on pdfsieve (which reads pages with pure-Python pdfminer.six), so it runs anywhere Pillow
and NumPy run, including PCs where policies block native PDF DLLs.

    >>> import pdfpainter
    >>> img = pdfpainter.render_pdf("statement.pdf", page=0, dpi=150)
    >>> img.save("statement-1.png")

The picture is simplified: shapes (with holes), lines, embedded images, and real text set in a
similar system font. Word and line positions match the PDF exactly, which is what OCR and
"draw a box over the page" interfaces need.
"""

from .fonts import FAMILIES, ITALICS, add_font_dir, family_for, find_font, font_dirs, font_for
from .images import decode_image
from .painter import MAX_PIXELS, page_size_px, render, render_pdf, to_ppm

__version__ = "0.1.0"

__all__ = [
    "render", "render_pdf", "page_size_px", "decode_image", "to_ppm",
    "add_font_dir", "font_dirs", "find_font", "font_for", "family_for", "FAMILIES", "ITALICS", "MAX_PIXELS",
    "__version__",
]
