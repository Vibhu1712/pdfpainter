"""Painting a pdfsieve page with Pillow."""

from __future__ import annotations

import math
from typing import Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageOps

from pdfsieve import Page, Picture, Shape

from .fonts import font_for
from .images import decode_image

MAX_PIXELS = 60_000_000
"""Pages with vector content are painted at twice the size and shrunk for smooth edges, unless
the doubled canvas would exceed this many pixels."""

R = Image.Resampling
T = Image.Transpose


# ---------------------------------------------------------------- shapes

def _flatten(pts, s: float) -> list:
    """A subpath as a polygon in pixels; curves become short straight pieces."""
    out = [(pts[0][1] * s, pts[0][2] * s)]
    for p in pts[1:]:
        if p[0] == "l":
            out.append((p[1] * s, p[2] * s))
        else:
            x0, y0 = out[-1]
            x1, y1, x2, y2, x3, y3 = (v * s for v in p[1:])
            span = abs(x1 - x0) + abs(y1 - y0) + abs(x2 - x1) + abs(y2 - y1) + abs(x3 - x2) + abs(y3 - y2)
            n = min(max(int(span / 3) + 1, 3), 32)
            for k in range(1, n + 1):
                t = k / n
                u = 1 - t
                a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
                out.append((a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3))
    return out


def _area(poly) -> float:
    a = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        a += x0 * y1 - x1 * y0
    return a / 2


def _fill(canvas: Image.Image, draw: ImageDraw.ImageDraw, polys, color, evenodd: bool) -> None:
    polys = [p for p in polys if len(p) >= 3]
    if not polys:
        return
    if len(polys) == 1:
        draw.polygon(polys[0], fill=color)
        return
    import numpy as np

    W, H = canvas.size
    x0 = max(int(math.floor(min(x for p in polys for x, _ in p))), 0)
    y0 = max(int(math.floor(min(y for p in polys for _, y in p))), 0)
    x1 = min(int(math.ceil(max(x for p in polys for x, _ in p))) + 1, W)
    y1 = min(int(math.ceil(max(y for p in polys for _, y in p))) + 1, H)
    if x1 <= x0 or y1 <= y0:
        return
    mask = np.zeros((y1 - y0, x1 - x0), dtype=bool)
    areas = [_area(p) for p in polys]
    order = sorted(range(len(polys)), key=lambda i: -abs(areas[i]))
    outer_sign = areas[order[0]] >= 0
    for i in order:
        p = polys[i]
        px0 = min(max(int(math.floor(min(x for x, _ in p))), x0), x1 - 1)
        py0 = min(max(int(math.floor(min(y for _, y in p))), y0), y1 - 1)
        px1 = max(min(int(math.ceil(max(x for x, _ in p))) + 1, x1), px0 + 1)
        py1 = max(min(int(math.ceil(max(y for _, y in p))) + 1, y1), py0 + 1)
        small = Image.new("1", (px1 - px0, py1 - py0), 0)
        ImageDraw.Draw(small).polygon([(x - px0, y - py0) for x, y in p], fill=1)
        sub = np.asarray(small, dtype=bool)
        view = mask[py0 - y0:py1 - y0, px0 - x0:px1 - x0]
        if evenodd:
            view ^= sub
        else:
            # Non-zero rule, approximated: biggest outlines first; an outline wound the other
            # way that lies inside ink is a hole (the inside of "o"), anything else is ink.
            inside = sub.any() and view[sub].mean() > 0.5
            if inside and (areas[i] >= 0) != outer_sign:
                view &= ~sub
            else:
                view |= sub
    canvas.paste(color, (x0, y0), Image.fromarray(mask.astype("uint8") * 255))


# ---------------------------------------------------------------- images

def _place(canvas: Image.Image, draw, pic: Picture, s: float) -> bool:
    """Paint one embedded image where its matrix puts it. False if it couldn't be decoded."""
    a, b, c, d, e, f = pic.matrix
    corners = [(e, f), (e + a, f + b), (e + c, f + d), (e + a + c, f + b + d)]
    bx0 = int(math.floor(min(x for x, _ in corners) * s))
    by0 = int(math.floor(min(y for _, y in corners) * s))
    bx1 = int(math.ceil(max(x for x, _ in corners) * s))
    by1 = int(math.ceil(max(y for _, y in corners) * s))
    bw, bh = bx1 - bx0, by1 - by0
    if bw < 1 or bh < 1 or bw * bh > 4 * canvas.size[0] * canvas.size[1]:
        return True
    img, stencil = decode_image(pic.stream)
    if img is None:
        draw.rectangle((bx0, by0, bx1, by1), fill=(236, 236, 236), outline=(170, 170, 170))
        return False
    if stencil:
        from pdfminer.pdftypes import resolve1

        dec = resolve1(pic.stream.get("Decode") or pic.stream.get("D"))
        paint_ones = bool(dec) and float(dec[0]) > float(dec[1])
        ink = img.convert("L")
        mask_src = ink if paint_ones else ImageOps.invert(ink)
        img = None
    else:
        mask_src = None
    src = img if img is not None else mask_src
    w, h = src.size
    if abs(b) < 1e-6 and abs(c) < 1e-6:  # upright: the usual case
        if a < 0:
            src = src.transpose(T.FLIP_LEFT_RIGHT)
        if d > 0:  # image's top row lands at the bottom
            src = src.transpose(T.FLIP_TOP_BOTTOM)
        small = bw < w or bh < h
        src = src.resize((bw, bh), R.LANCZOS if small else R.BICUBIC)
        valid = None
    else:  # rotated or skewed
        # image pixel (i, j) -> canvas: u = i / w, v = 1 - j / h
        m00, m01, m02 = s * a / w, -s * c / h, s * (c + e) - bx0
        m10, m11, m12 = s * b / w, -s * d / h, s * (d + f) - by0
        det = m00 * m11 - m01 * m10
        if abs(det) < 1e-12:
            return True
        i00, i01, i10, i11 = m11 / det, -m01 / det, -m10 / det, m00 / det
        coeffs = (i00, i01, -(i00 * m02 + i01 * m12), i10, i11, -(i10 * m02 + i11 * m12))
        valid = Image.new("L", (w, h), 255).transform((bw, bh), Image.Transform.AFFINE, coeffs, R.NEAREST)
        src = src.transform((bw, bh), Image.Transform.AFFINE, coeffs, R.BICUBIC)
    if mask_src is not None:  # stencil: paint the fill colour through the mask
        if valid is not None:
            src = ImageChops.multiply(src, valid)
        canvas.paste(pic.color or (0, 0, 0), (bx0, by0), src)
    else:
        canvas.paste(src.convert("RGB"), (bx0, by0), valid)
    return True


# ---------------------------------------------------------------- page

def page_size_px(page: Page, zoom: float) -> Tuple[int, int]:
    """The size in pixels :func:`render` produces: the same rounding PDFium uses, so the two are
    interchangeable."""
    return (max(math.ceil(page.width * zoom - 1e-6), 1), max(math.ceil(page.height * zoom - 1e-6), 1))


def render(page: Page, zoom: float = 1.0, info: Optional[dict] = None, *, dpi: Optional[float] = None,
           background: Tuple[int, int, int] = (255, 255, 255), text: bool = True,
           antialias: bool = True) -> Image.Image:
    """Paint a page as an RGB Pillow image.

    zoom:       pixels per point (1.0 = 72 dpi). ``dpi`` sets the same thing in dots per inch.
    info:       a dict that receives ``undecoded`` (images that could not be shown) and
                ``skipped_fills`` (shapes filled with a pattern or shading, left out).
    background: page colour.
    text:       False leaves real text out (shapes and images only), e.g. to see what a page
                looks like to OCR once its text layer is ignored.
    antialias:  paint vector pages at twice the size and shrink, for smooth edges.
    """
    if dpi is not None:
        zoom = dpi / 72.0
    if zoom <= 0:
        raise ValueError("zoom must be positive")
    W, H = page_size_px(page, zoom)
    has_vector = bool(page.glyphs) or any(isinstance(i, Shape) for i in page.items)
    ss = 2 if antialias and has_vector and W * H * 4 <= MAX_PIXELS else 1
    s = zoom * ss
    canvas = Image.new("RGB", (W * ss, H * ss), background)
    draw = ImageDraw.Draw(canvas)
    undecoded = skipped = 0
    for it in page.items:
        if isinstance(it, Picture):
            if not _place(canvas, draw, it, s):
                undecoded += 1
            continue
        polys = [(_flatten(pts, s), closed) for pts, closed in it.subpaths]
        if it.fill is not None:
            _fill(canvas, draw, [p for p, _ in polys], it.fill, it.evenodd)
        elif it.stroke is None:
            skipped += 1
        if it.stroke is not None:
            width = max(int(round(it.width * s)), ss)
            for p, closed in polys:
                if closed:
                    p = p + p[:1]
                if len(p) >= 2:
                    draw.line(p, fill=it.stroke, width=width, joint="curve" if width > 2 else None)
    if text:
        for g in page.glyphs:
            if not g.visible or not g.text.strip() or g.text == "�":
                continue
            px = max(int(round(g.size * s)), 4)
            font = font_for(g.font, g.text, px)
            if not g.upright:
                _sideways(canvas, g, font, px, s)
                continue
            try:
                draw.text((g.x0 * s, g.base * s), g.text, font=font, fill=g.color or (0, 0, 0), anchor="ls")
            except Exception:  # bitmap fallback font has no anchors
                draw.text((g.x0 * s, g.y0 * s), g.text, font=font, fill=g.color or (0, 0, 0))
    if info is not None:
        info["undecoded"] = undecoded
        info["skipped_fills"] = skipped
    return canvas.resize((W, H), R.LANCZOS) if ss > 1 else canvas


def _sideways(canvas: Image.Image, g, font, px: int, s: float) -> None:
    """A character that is turned on the page: set it upright on a scrap, turn the scrap, and
    stamp it so its baseline corner sits where the PDF put it."""
    try:
        pad = px
        scrap = Image.new("L", (px * 2 + 2 * pad, px * 2 + 2 * pad), 0)
        ImageDraw.Draw(scrap).text((scrap.width // 2, scrap.height // 2), g.text, font=font, fill=255,
                                   anchor="ls")
        scrap = scrap.rotate(g.turn)  # turns about the centre, where the baseline starts
        # the baseline start in the box: the corner the writing leaves from
        ox, oy = {90: (g.x1, g.y1), 180: (g.x1, g.y0), 270: (g.x0, g.y0)}.get(g.turn, (g.x0, g.y1))
        d = 0.22 * g.size  # the box includes the descender; lift the baseline off the box edge
        ox, oy = {90: (ox - d, oy), 180: (ox, oy + d), 270: (ox + d, oy)}.get(g.turn, (ox, oy - d))
        canvas.paste(g.color or (0, 0, 0),
                     (int(round(ox * s - scrap.width / 2)), int(round(oy * s - scrap.height / 2))), scrap)
    except Exception:
        pass


def render_pdf(source, page: int = 0, zoom: float = 1.0, *, dpi: Optional[float] = None, password: str = "",
               info: Optional[dict] = None, **kwargs) -> Image.Image:
    """Open a PDF (path, bytes or binary file) and paint one page (0-based). Other keyword
    arguments go to :func:`render`."""
    import pdfsieve

    with pdfsieve.open(source, password=password) as doc:
        return render(doc.page(page), zoom, info, dpi=dpi, **kwargs)


def to_ppm(img: Image.Image) -> bytes:
    """PPM bytes, which Tk's ``PhotoImage`` reads without any extra library."""
    img = img.convert("RGB")
    return b"P6 %d %d 255\n" % img.size + img.tobytes()
