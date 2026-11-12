"""Make sample.pdf, a payslip-style page used in the README examples.

    pip install reportlab
    python examples/make_sample_pdf.py
"""

import sys

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

out = sys.argv[1] if len(sys.argv) > 1 else "sample.pdf"
W, H = A4
c = canvas.Canvas(out, pagesize=A4)
c.setTitle("Sample payslip")


def top(y):
    return H - y


# header bar and a ring logo (two circles, even-odd fill)
c.setFillColorRGB(0.11, 0.25, 0.45)
c.rect(0, top(90), W, 90, stroke=0, fill=1)
c.setFillColorRGB(1, 1, 1)
logo = c.beginPath()
logo.circle(75, top(45), 24)
logo.circle(75, top(45), 13)
c.drawPath(logo, stroke=0, fill=1, fillMode=0)
c.setFont("Helvetica-Bold", 22)
c.drawString(115, top(52), "Acme Industries Pvt Ltd")
c.setFont("Helvetica", 10)
c.drawString(115, top(70), "Payslip for October 2026")

# a photo-like gradient image
grad = Image.new("RGB", (64, 64))
grad.putdata([(40 + 3 * x, 90 + 2 * y, 160) for y in range(64) for x in range(64)])
c.drawImage(ImageReader(grad), W - 132, top(200), width=80, height=80)

c.setFillColorRGB(0, 0, 0)
c.setFont("Helvetica", 11)
for i, (k, v) in enumerate((("Employee", "Meera Sharma"), ("Employee ID", "EMP-0042"),
                            ("Department", "Finance"))):
    c.drawString(60, top(140 + 20 * i), k)
    c.drawString(160, top(140 + 20 * i), ": " + v)

# earnings table
rows = [("Component", "Earnings", "Deductions"), ("Basic pay", "52,000.00", ""),
        ("House rent allowance", "20,800.00", ""), ("Provident fund", "", "6,240.00"),
        ("Professional tax", "", "200.00"), ("Net pay", "66,360.00", "")]
x_cols, y0, rh = (60, 280, 420, 535), 240, 24
c.setLineWidth(0.8)
c.setFillColorRGB(0.92, 0.94, 0.97)
c.rect(60, top(y0 + rh), 475, rh, stroke=0, fill=1)
c.setFillColorRGB(0, 0, 0)
for x in x_cols:
    c.line(x, top(y0), x, top(y0 + rh * len(rows)))
for r in range(len(rows) + 1):
    c.line(60, top(y0 + rh * r), 535, top(y0 + rh * r))
for r, row in enumerate(rows):
    c.setFont("Helvetica-Bold" if r in (0, len(rows) - 1) else "Helvetica", 10.5)
    for col, text in enumerate(row):
        if col == 0:
            c.drawString(x_cols[0] + 8, top(y0 + rh * r + 16), text)
        elif text:
            c.drawRightString(x_cols[col + 1] - 8, top(y0 + rh * r + 16), text)

c.setFont("Times-Italic", 10)
c.drawString(60, top(420), "This is a computer-generated payslip and needs no signature.")

# sideways margin note
c.saveState()
c.translate(30, top(700))
c.rotate(90)
c.setFont("Helvetica", 8)
c.setFillColorRGB(0.5, 0.5, 0.5)
c.drawString(0, 0, "Sample document for pdfsieve and pdfpainter")
c.restoreState()
c.showPage()
c.save()
print("wrote", out)
