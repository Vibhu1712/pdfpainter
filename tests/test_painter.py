from __future__ import annotations

import os

import numpy as np
import pytest

import pdfpainter
import pdfsieve
from pdfpainter.__main__ import main, out_name, parse_pages

Z = 2.0  # 2 pixels per point in most tests


def px(img, x, y, z=Z):
    """Colour at page point (x, y)."""
    return img.getpixel((int(x * z), int(y * z)))


def near(rgb, want, tol=8):
    """Colours match within a few levels (scaling a tiny image up blurs its edges a little)."""
    return all(abs(a - b) <= tol for a, b in zip(rgb, want))


def dark(rgb, limit=100):
    return max(rgb) < limit


def ink(img, box, z=Z):
    """Fraction of dark pixels inside a page-space box."""
    a = np.asarray(img.convert("L"))
    x0, y0, x1, y1 = (int(round(v * z)) for v in box)
    return float((a[y0:y1, x0:x1] < 128).mean())


def test_size_matches_pdfium_rounding(pdfs):
    with pdfsieve.open(pdfs["invoice"]) as doc:
        page = doc.page(0)
        for zoom in (0.5, 1.0, 2.0, 300 / 72):
            img = pdfpainter.render(page, zoom)
            assert img.mode == "RGB"
            assert img.size == pdfpainter.page_size_px(page, zoom)
        assert pdfpainter.render(page, dpi=144).size == pdfpainter.render(page, 2.0).size
    pdfium = pytest.importorskip("pypdfium2")
    pdf = pdfium.PdfDocument(pdfs["invoice"])
    for zoom in (1.0, 2.0, 300 / 72):
        assert pdf[0].render(scale=zoom).to_pil().size == pdfpainter.render_pdf(pdfs["invoice"], 0, zoom).size
    pdf.close()


def test_shapes_lines_and_text(pdfs):
    img = pdfpainter.render_pdf(pdfs["invoice"], 0, Z)
    assert px(img, 450, 275)[0] > 200 and px(img, 450, 275)[1] < 60  # inside the red box
    assert px(img, 395, 275) == (255, 255, 255)  # just outside it
    assert dark(px(img, 72, 160)) and dark(px(img, 300, 175))  # table rules
    with pdfsieve.open(pdfs["invoice"]) as doc:
        words = doc.page(0).words()
    for w in words:  # every word has ink inside its box...
        assert ink(img, w[:4]) > 0.05, w.text
    assert ink(img, (100, 400, 500, 800)) == 0  # ...and the empty part of the page has none


def test_text_can_be_left_out(pdfs):
    img = pdfpainter.render_pdf(pdfs["invoice"], 0, Z, text=False)
    assert ink(img, (72, 64, 200, 84)) == 0  # where "Invoice No" was
    assert dark(px(img, 72, 160))  # lines stay


def test_fill_rules(pdfs):
    img = pdfpainter.render_pdf(pdfs["rings"], 0, Z)
    assert dark(px(img, 150, 110)) and not dark(px(img, 150, 150))  # even-odd ring: hole
    assert dark(px(img, 310, 150)) and not dark(px(img, 350, 150))  # non-zero, opposite winding
    assert dark(px(img, 460, 150)) and dark(px(img, 500, 150))  # non-zero, same winding: solid


def test_image_and_sideways_text(pdfs):
    img = pdfpainter.render_pdf(pdfs["image"], 0, Z)
    assert near(px(img, 200, 250), (0, 128, 255))
    assert px(img, 95, 250) == (255, 255, 255) and px(img, 305, 250) == (255, 255, 255)
    with pdfsieve.open(pdfs["image"]) as doc:
        word = doc.page(0).words()[0]
    assert word.text == "UPWARDS" and word.height > word.width
    assert ink(img, word[:4]) > 0.1  # drawn turned, inside its tall box


def test_image_kinds(pdfs):
    info = {}
    img = pdfpainter.render_pdf(pdfs["kinds"], 0, 1.0, info=info)
    # stencil at (10, 10)-(90, 90): left half painted in the current fill colour (blue)
    assert near(px(img, 30, 50, 1), (0, 0, 255)) and px(img, 70, 50, 1) == (255, 255, 255)
    # indexed at (110, 10)-(190, 90): row 0 red, green; row 1 green, red
    assert near(px(img, 130, 30, 1), (255, 0, 0)) and near(px(img, 170, 30, 1), (0, 255, 0))
    assert near(px(img, 130, 70, 1), (0, 255, 0))
    # CMYK at (10, 110)-(90, 190): red
    assert near(px(img, 50, 150, 1), (255, 0, 0))
    # JBIG2 at (110, 110)-(190, 190): unsupported, shown as a grey placeholder and counted
    assert px(img, 150, 150, 1) == (236, 236, 236)
    assert info == {"undecoded": 1, "skipped_fills": 0}


def test_16_bit_gray(pdfs):
    img = pdfpainter.render_pdf(pdfs["gray16"], 0, 1.0)
    # 100x100 at (50, 50): each row is white then black
    assert near(px(img, 75, 75, 1), (255, 255, 255)) and near(px(img, 125, 75, 1), (0, 0, 0))


def test_decode_image_direct(pdfs):
    with pdfsieve.open(pdfs["kinds"]) as doc:
        pics = doc.page(0).pictures
    stencil, is_stencil = pdfpainter.decode_image(pics[0].stream)
    assert is_stencil and stencil.size == (8, 8) and stencil.mode == "1"
    indexed, is_stencil = pdfpainter.decode_image(pics[1].stream)
    assert not is_stencil and indexed.getpixel((0, 0)) == (255, 0, 0)
    assert pdfpainter.decode_image(pics[3].stream) == (None, False)


def test_ppm_and_bad_zoom(pdfs):
    img = pdfpainter.render_pdf(pdfs["rings"], 0, 0.5)
    data = pdfpainter.to_ppm(img)
    assert data.startswith(b"P6 %d %d 255\n" % img.size)
    assert len(data) == len(b"P6 %d %d 255\n" % img.size) + img.width * img.height * 3
    with pytest.raises(ValueError):
        pdfpainter.render_pdf(pdfs["rings"], 0, 0)


def test_fonts():
    assert pdfpainter.family_for("ABCDEF+Arial-BoldMT", "A") == "sans"
    assert pdfpainter.family_for("TimesNewRomanPSMT", "A") == "serif"
    assert pdfpainter.family_for("CourierNewPSMT", "A") == "mono"
    assert pdfpainter.family_for("Arial", "क") == "indic"  # Devanagari KA
    assert pdfpainter.family_for("Arial", "中") == "cjk"
    assert pdfpainter.family_for("Arial", "ﬁ") == "sans"  # ligature block isn't CJK
    font = pdfpainter.font_for("Helvetica-Bold", "A", 20)
    assert font is not None
    upright = pdfpainter.find_font("serif", False)
    italic = pdfpainter.find_font("serif", False, italic=True)
    if upright and italic:  # needs serif fonts installed
        assert italic != upright


def test_add_font_dir(tmp_path):
    dirs_before = pdfpainter.font_dirs()
    pdfpainter.add_font_dir(str(tmp_path))
    assert pdfpainter.font_dirs()[0] == str(tmp_path)
    assert pdfpainter.font_dirs()[1:] == dirs_before


def test_cli(pdfs, tmp_path, capsys):
    out = str(tmp_path / "page.png")
    assert main([pdfs["invoice"], "-o", out, "--dpi", "72"]) == 0
    assert os.path.isfile(out)
    assert "(596 x 842)" in capsys.readouterr().out
    assert main([pdfs["kinds"], "-o", str(tmp_path / "k-{page}.jpg")]) == 0
    assert os.path.isfile(tmp_path / "k-1.jpg")
    assert "1 image(s) in an unsupported format" in capsys.readouterr().out
    assert main([pdfs["invoice"], "-p", "3"]) == 2
    assert main([str(tmp_path / "missing.pdf")]) == 2


def test_cli_helpers():
    assert parse_pages("2-3", 4) == [1, 2]
    assert out_name("a.png", 0, False) == "a.png"
    assert out_name("a.png", 2, True) == "a-3.png"
    assert out_name("p{page}.tif", 4, True) == "p5.tif"
