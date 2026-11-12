"""Finding a system font similar to the PDF's font.

pdfpainter never uses the fonts embedded in the PDF. It sets real text in a font from this
computer that matches the family (sans, serif, mono), weight, slant, and script (Latin, Indic,
CJK).
Extra font folders can be added with :func:`add_font_dir` or the ``PDFPAINTER_FONT_DIRS``
environment variable (folders separated by ``os.pathsep``).
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Tuple

from PIL import ImageFont

ENV_FONT_DIRS = "PDFPAINTER_FONT_DIRS"

# family -> (regular candidates, bold candidates), first found wins
FAMILIES: Dict[str, Tuple[List[str], List[str]]] = {
    "sans": (["arial.ttf", "Arial.ttf", "LiberationSans-Regular.ttf", "segoeui.ttf", "DejaVuSans.ttf",
              "FreeSans.ttf"],
             ["arialbd.ttf", "Arial Bold.ttf", "LiberationSans-Bold.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf",
              "FreeSansBold.ttf"]),
    "serif": (["times.ttf", "Times New Roman.ttf", "LiberationSerif-Regular.ttf", "DejaVuSerif.ttf",
               "FreeSerif.ttf"],
              ["timesbd.ttf", "Times New Roman Bold.ttf", "LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf",
               "FreeSerifBold.ttf"]),
    "mono": (["cour.ttf", "Courier New.ttf", "LiberationMono-Regular.ttf", "DejaVuSansMono.ttf",
              "FreeMono.ttf"],
             ["courbd.ttf", "Courier New Bold.ttf", "LiberationMono-Bold.ttf", "DejaVuSansMono-Bold.ttf",
              "FreeMonoBold.ttf"]),
    # scripts the Latin fonts above don't cover
    "indic": (["Nirmala.ttf", "Nirmala.ttc", "mangal.ttf", "NotoSansDevanagari-Regular.ttf", "Kohinoor.ttc"],
              ["NirmalaB.ttf", "Nirmala.ttc", "NotoSansDevanagari-Bold.ttf"]),
    "cjk": (["YuGothR.ttc", "msgothic.ttc", "msyh.ttc", "malgun.ttf", "NotoSansCJK-Regular.ttc",
             "NotoSansCJKjp-Regular.otf", "PingFang.ttc"],
            ["YuGothB.ttc", "msyhbd.ttc", "malgunbd.ttf", "NotoSansCJK-Bold.ttc"]),
}

# family -> (italic candidates, bold italic candidates); scripts without italics fall back upright
ITALICS: Dict[str, Tuple[List[str], List[str]]] = {
    "sans": (["ariali.ttf", "Arial Italic.ttf", "LiberationSans-Italic.ttf", "segoeuii.ttf",
              "DejaVuSans-Oblique.ttf", "FreeSansOblique.ttf"],
             ["arialbi.ttf", "Arial Bold Italic.ttf", "LiberationSans-BoldItalic.ttf", "segoeuiz.ttf",
              "DejaVuSans-BoldOblique.ttf", "FreeSansBoldOblique.ttf"]),
    "serif": (["timesi.ttf", "Times New Roman Italic.ttf", "LiberationSerif-Italic.ttf", "DejaVuSerif-Italic.ttf",
               "FreeSerifItalic.ttf"],
              ["timesbi.ttf", "Times New Roman Bold Italic.ttf", "LiberationSerif-BoldItalic.ttf",
               "DejaVuSerif-BoldItalic.ttf", "FreeSerifBoldItalic.ttf"]),
    "mono": (["couri.ttf", "Courier New Italic.ttf", "LiberationMono-Italic.ttf", "DejaVuSansMono-Oblique.ttf",
              "FreeMonoOblique.ttf"],
             ["courbi.ttf", "Courier New Bold Italic.ttf", "LiberationMono-BoldItalic.ttf",
              "DejaVuSansMono-BoldOblique.ttf", "FreeMonoBoldOblique.ttf"]),
}

_extra_dirs: List[str] = []
_paths: Dict[Tuple[str, bool, bool], Optional[str]] = {}
_fonts: Dict[Tuple[str, bool, bool, int], object] = {}


def add_font_dir(path: str) -> None:
    """Search this folder for fonts before the system folders."""
    if path not in _extra_dirs:
        _extra_dirs.insert(0, path)
    _paths.clear()
    _fonts.clear()


def font_dirs() -> List[str]:
    """Folders searched for fonts, in order."""
    env = [d for d in os.environ.get(ENV_FONT_DIRS, "").split(os.pathsep) if d]
    if os.name == "nt":
        system = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")]
    elif sys.platform == "darwin":
        system = ["/System/Library/Fonts/Supplemental", "/System/Library/Fonts", "/Library/Fonts",
                  os.path.expanduser("~/Library/Fonts")]
    else:
        system = ["/usr/share/fonts/truetype/liberation", "/usr/share/fonts/truetype/dejavu",
                  "/usr/share/fonts/truetype/freefont", "/usr/share/fonts/truetype/noto",
                  "/usr/share/fonts/opentype/noto", "/usr/share/fonts/liberation",
                  "/usr/share/fonts/dejavu", "/usr/share/fonts", os.path.expanduser("~/.local/share/fonts")]
    return _extra_dirs + env + system


def find_font(family: str, bold: bool, italic: bool = False) -> Optional[str]:
    """Path of the first installed font for a family and style, or None. A bold or italic
    request falls back to the plainer styles of the same family."""
    key = (family, bold, italic)
    if key not in _paths:
        found = None
        regular, bolds = FAMILIES[family]
        italics, bold_italics = ITALICS.get(family, ([], []))
        if italic:
            names = (bold_italics + italics + bolds + regular) if bold else (italics + regular)
        else:
            names = (bolds + regular) if bold else regular
        dirs = font_dirs()
        for name in names:
            for d in dirs:
                p = os.path.join(d, name)
                if os.path.isfile(p):
                    found = p
                    break
            if found:
                break
        _paths[key] = found
    return _paths[key]


def family_for(fontname: str, ch: str) -> str:
    """Which family to draw a character in: by its script first, then by the PDF font's name."""
    o = ord(ch[0]) if ch else 0
    if 0x0900 <= o <= 0x0DFF:
        return "indic"
    if o >= 0x2E80 and not 0xFB00 <= o <= 0xFB4F:
        return "cjk"
    n = fontname.lower()
    if any(k in n for k in ("courier", "mono", "consol")):
        return "mono"
    if any(k in n for k in ("times", "serif", "roman", "georgia", "cambria", "garamond", "minion")) \
            and "sans" not in n:
        return "serif"
    return "sans"


def font_for(fontname: str, ch: str, px: int):
    """A Pillow font, ``px`` pixels high, to draw ``ch`` in place of the PDF font ``fontname``."""
    name = fontname.lower()
    bold = any(k in name for k in ("bold", "black", "heavy", "semibold"))
    italic = any(k in name for k in ("italic", "oblique", "slant"))
    fam = family_for(fontname, ch)
    key = (fam, bold, italic, px)
    if key not in _fonts:
        path = find_font(fam, bold, italic) or find_font("sans", bold, italic) or find_font("sans", False)
        font = None
        if path:
            try:
                font = ImageFont.truetype(path, px)
            except Exception:
                font = None
        if font is None:
            try:
                font = ImageFont.load_default(size=px)  # Pillow >= 10.1: scalable built-in font
            except TypeError:  # older Pillow: fixed tiny bitmap font
                font = ImageFont.load_default()
        _fonts[key] = font
    return _fonts[key]
