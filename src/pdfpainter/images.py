"""Decoding images embedded in a PDF into Pillow images, without a PDF engine."""

from __future__ import annotations

import io
from typing import Optional, Tuple

from PIL import Image, ImageOps


def _name(obj) -> str:
    n = getattr(obj, "name", obj)
    if isinstance(n, bytes):
        n = n.decode("latin-1")
    return str(n)


def decode_image(stream) -> Tuple[Optional[Image.Image], bool]:
    """An embedded image (a pdfminer ``PDFStream``) as ``(picture, is_stencil)``.

    Supported: JPEG (DCT), JPEG 2000 (JPX, if your Pillow reads it), and raw/Flate/LZW/RunLength samples in gray, RGB, CMYK,
    ICC-based, calibrated and indexed colour spaces at 1, 2, 4, 8 or 16 bits per component, plus
    1-bit stencil masks. Returns ``(None, False)`` for anything else (JBIG2, DeviceN and other
    unusual colour spaces).

    For a stencil the picture is the raw 1-bit mask; the caller paints the fill colour where the
    sample is 0 (or 1 when the image's /Decode array is inverted).
    """
    from pdfminer.pdftypes import PDFStream, resolve1

    def get(*keys, default=None):
        for k in keys:
            if k in stream:
                return resolve1(stream[k])
        return default

    try:
        filters = [_name(f) for f, _ in stream.get_filters()]
        last = filters[-1] if filters else ""
        if last == "JBIG2Decode":
            return None, False
        data = stream.get_data()
        w, h = int(get("Width", "W")), int(get("Height", "H"))
        stencil = bool(get("ImageMask", "IM", default=False))
        decode = get("Decode", "D")
        inverted = bool(decode) and float(decode[0]) > float(decode[1])
        if last in ("DCTDecode", "DCT", "JPXDecode"):
            img = Image.open(io.BytesIO(data))
            img.load()
            if img.mode == "CMYK":
                # Adobe JPEGs store CMYK inverted; Pillow already handles the common case
                img = img.convert("RGB")
            return img.convert("RGB" if img.mode != "L" else "L"), False
        bpc = int(get("BitsPerComponent", "BPC", default=1 if stencil else 8))
        cs = get("ColorSpace", "CS")
        palette = None
        if isinstance(cs, list):
            kind = _name(cs[0])
            if kind in ("Indexed", "I"):
                base = resolve1(cs[1])
                base_n = {"DeviceGray": 1, "G": 1, "DeviceCMYK": 4, "CMYK": 4}.get(
                    _name(base[0] if isinstance(base, list) else base), 3)
                if isinstance(base, list) and _name(base[0]) == "ICCBased":
                    base_n = int(resolve1(base[1]).get("N", 3))
                look = resolve1(cs[3])
                look = look.get_data() if isinstance(look, PDFStream) else bytes(look)
                palette = (base_n, look)
                ncomp = 1
            elif kind == "ICCBased":
                ncomp = int(resolve1(cs[1]).get("N", 3))
            elif kind in ("CalGray", "Separation"):
                ncomp = 1
            elif kind in ("CalRGB", "Lab"):
                ncomp = 3
            else:
                return None, False
        else:
            ncomp = {"DeviceGray": 1, "G": 1, "DeviceRGB": 3, "RGB": 3, "DeviceCMYK": 4, "CMYK": 4}.get(
                _name(cs) if cs is not None else "DeviceGray", 1)
        if stencil:
            ncomp, bpc = 1, 1

        if bpc == 1 and ncomp == 1 and palette is None:
            img = Image.frombytes("1", (w, h), data[: ((w + 7) // 8) * h])
            if stencil:
                return img, True
            img = img.convert("L")
        else:
            import numpy as np

            row = (w * ncomp * bpc + 7) // 8
            arr = np.frombuffer(data[: row * h], dtype=np.uint8).reshape(h, row)
            if bpc == 8:
                px = arr[:, : w * ncomp]
            elif bpc == 16:
                px = arr[:, : w * ncomp * 2: 2]
            elif bpc in (1, 2, 4):
                bits = np.unpackbits(arr, axis=1)[:, : w * ncomp * bpc].reshape(h, w * ncomp, bpc)
                px = bits.dot(1 << np.arange(bpc - 1, -1, -1)).astype(np.uint8)
                if palette is None:
                    px = (px.astype(np.uint16) * 255 // ((1 << bpc) - 1)).astype(np.uint8)
            else:
                return None, False
            px = np.ascontiguousarray(px)
            if palette is not None:
                base_n, look = palette
                table = np.frombuffer(look, dtype=np.uint8)
                table = table[: (len(table) // base_n) * base_n].reshape(-1, base_n)
                if base_n == 1:
                    table = np.repeat(table, 3, axis=1)
                elif base_n == 4:
                    k = table[:, 3:4].astype(np.int32)
                    table = (255 - np.minimum(255, table[:, :3].astype(np.int32) + k)).astype(np.uint8)
                idx = np.minimum(px, len(table) - 1)
                img = Image.fromarray(np.ascontiguousarray(table[idx]))
            elif ncomp == 1:
                img = Image.fromarray(px.reshape(h, w))
            elif ncomp == 3:
                img = Image.fromarray(px.reshape(h, w, 3))
            elif ncomp == 4:
                img = Image.frombytes("CMYK", (w, h), px.tobytes()).convert("RGB")
            else:
                return None, False
        if inverted and not stencil:
            img = ImageOps.invert(img.convert("L") if img.mode == "1" else img)
        return img, False
    except Exception:
        return None, False
