"""Sample PDFs are generated on the fly, so the repository holds no binary files."""

from __future__ import annotations

import zlib

import pytest

reportlab = pytest.importorskip("reportlab")
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

W, H = A4


def top(y: float) -> float:
    return H - y


def raw_pdf(content: bytes, xobjects: dict, size=(200, 200)) -> bytes:
    """A one-page PDF built by hand. xobjects: name -> (dict entries as bytes, stream data)."""
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", None, None, None]
    xrefs = []
    for i, (name, (entries, data)) in enumerate(xobjects.items()):
        num = 5 + i
        xrefs.append(b"/%s %d 0 R" % (name.encode(), num))
        objs.append(b"<< /Type /XObject /Subtype /Image %s /Length %d >>\nstream\n%s\nendstream"
                    % (entries, len(data), data))
    objs[1] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    objs[2] = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Contents 4 0 R "
               b"/Resources << /XObject << %s >> >> >>" % (size[0], size[1], b" ".join(xrefs)))
    objs[3] = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content)
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (n, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


@pytest.fixture(scope="session")
def pdfs(tmp_path_factory):
    d = tmp_path_factory.mktemp("pdfs")
    out = {}

    # invoice: text, table lines, a red box
    p = str(d / "invoice.pdf")
    c = canvas.Canvas(p, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, top(80), "Invoice No 1234")
    c.setFont("Helvetica", 11)
    c.setLineWidth(1)
    for x in (72, 222, 372, 522):
        c.line(x, top(150), x, top(200))
    for y in (150, 175, 200):
        c.line(72, top(y), 522, top(y))
    c.drawString(80, top(168), "Item")
    c.drawString(380, top(193), "5,000.00")
    c.setFillColorRGB(1, 0, 0)
    c.rect(400, top(300), 100, 50, stroke=0, fill=1)  # (400, 250)-(500, 300)
    c.showPage()
    c.save()
    out["invoice"] = p

    # ring "O" drawn as outlines, even-odd and non-zero
    p = str(d / "rings.pdf")
    c = canvas.Canvas(p, pagesize=A4)
    path = c.beginPath()
    path.circle(150, top(150), 50)
    path.circle(150, top(150), 25)
    c.drawPath(path, stroke=0, fill=1, fillMode=0)  # even-odd: hole
    path = c.beginPath()  # non-zero, outer clockwise and inner anticlockwise: hole
    path.moveTo(300, top(100)); path.lineTo(400, top(100)); path.lineTo(400, top(200))
    path.lineTo(300, top(200)); path.close()
    path.moveTo(325, top(125)); path.lineTo(325, top(175)); path.lineTo(375, top(175))
    path.lineTo(375, top(125)); path.close()
    c.drawPath(path, stroke=0, fill=1, fillMode=1)
    path = c.beginPath()  # non-zero, both clockwise: no hole
    path.moveTo(450, top(100)); path.lineTo(550, top(100)); path.lineTo(550, top(200))
    path.lineTo(450, top(200)); path.close()
    path.moveTo(475, top(125)); path.lineTo(525, top(125)); path.lineTo(525, top(175))
    path.lineTo(475, top(175)); path.close()
    c.drawPath(path, stroke=0, fill=1, fillMode=1)
    c.showPage()
    c.save()
    out["rings"] = p

    # an embedded RGB image and sideways text
    from PIL import Image

    p = str(d / "image.pdf")
    ip = str(d / "blue.png")
    Image.new("RGB", (40, 20), (0, 128, 255)).save(ip)
    c = canvas.Canvas(p, pagesize=A4)
    c.drawImage(ip, 100, top(300), width=200, height=100)  # (100, 200)-(300, 300)
    c.setFont("Helvetica", 30)
    c.saveState()
    c.translate(450, top(600))
    c.rotate(90)
    c.drawString(0, 0, "UPWARDS")
    c.restoreState()
    c.showPage()
    c.save()
    out["image"] = p

    # hand-made image kinds: 1-bit stencil, indexed, CMYK, 16-bit gray, JBIG2 (unsupported)
    stencil = bytes([0b00001111]) * 8  # 8x8: left half 0 = painted, right half 1 = clear
    indexed = bytes([0, 1, 1, 0])      # 2x2 with palette red, green
    cmyk = bytes([0, 255, 255, 0]) * 4  # 2x2 red in CMYK
    gray16 = b"\xff\xff\x00\x00" * 2   # 2x2: white, black per row
    content = (b"0 0 1 rg q 80 0 0 80 10 110 cm /S Do Q "
               b"q 80 0 0 80 110 110 cm /I Do Q "
               b"q 80 0 0 80 10 10 cm /C Do Q "
               b"q 80 0 0 80 110 10 cm /J Do Q")
    out["kinds"] = str(d / "kinds.pdf")
    with open(out["kinds"], "wb") as f:
        f.write(raw_pdf(content, {
            "S": (b"/Width 8 /Height 8 /ImageMask true /BitsPerComponent 1 /Filter /FlateDecode",
                  zlib.compress(stencil)),
            "I": (b"/Width 2 /Height 2 /BitsPerComponent 8 /ColorSpace [/Indexed /DeviceRGB 1 <FF000000FF00>]",
                  indexed),
            "C": (b"/Width 2 /Height 2 /BitsPerComponent 8 /ColorSpace /DeviceCMYK", cmyk),
            "J": (b"/Width 2 /Height 2 /BitsPerComponent 1 /ColorSpace /DeviceGray /Filter /JBIG2Decode",
                  b"\x00" * 8),
        }))
    out["gray16"] = str(d / "gray16.pdf")
    with open(out["gray16"], "wb") as f:
        f.write(raw_pdf(b"q 100 0 0 100 50 50 cm /G Do Q", {
            "G": (b"/Width 2 /Height 2 /BitsPerComponent 16 /ColorSpace /DeviceGray", gray16)}))
    return out
