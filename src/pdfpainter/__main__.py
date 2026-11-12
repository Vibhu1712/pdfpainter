"""Command line: ``pdfpainter file.pdf -o page.png`` (or ``python -m pdfpainter ...``)."""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

import pdfsieve

from . import __version__, render


def parse_pages(spec: Optional[str], count: int) -> List[int]:
    """'1,3-5' -> [0, 2, 3, 4] (1-based in, 0-based out). None means every page."""
    if not spec:
        return list(range(count))
    out: List[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            lo = int(a) if a.strip() else 1
            hi = int(b) if b.strip() else count
        else:
            lo = hi = int(part)
        for n in range(lo, hi + 1):
            if not 1 <= n <= count:
                raise ValueError(f"page {n} out of range (the PDF has {count} pages)")
            if n - 1 not in out:
                out.append(n - 1)
    return out


def out_name(pattern: str, page: int, many: bool) -> str:
    """'{page}' in the name becomes the 1-based page number; with several pages and no
    '{page}', '-N' goes before the extension."""
    if "{page}" in pattern:
        return pattern.replace("{page}", str(page + 1))
    if many:
        root, ext = os.path.splitext(pattern)
        return f"{root}-{page + 1}{ext}"
    return pattern


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="pdfpainter",
        description="Paint PDF pages to image files with Pillow alone (simplified rendering, "
                    "exact positions).")
    ap.add_argument("pdf", help="the PDF file")
    ap.add_argument("-o", "--output", default=None,
                    help="image file to write; the extension picks the format (.png, .jpg, .tif...). "
                         "'{page}' is replaced by the page number. Default: <pdf name>-{page}.png")
    ap.add_argument("-p", "--pages", help="pages, 1-based, e.g. 1,3-5 (default: all)")
    ap.add_argument("-d", "--dpi", type=float, default=150.0, help="resolution (default: 150)")
    ap.add_argument("--no-text", action="store_true", help="leave real text out (shapes and images only)")
    ap.add_argument("--password", default="", help="password for an encrypted PDF")
    ap.add_argument("-V", "--version", action="version", version=f"pdfpainter {__version__}")
    args = ap.parse_args(argv)

    if args.dpi <= 0:
        print("pdfpainter: --dpi must be positive", file=sys.stderr)
        return 2
    try:
        doc = pdfsieve.open(args.pdf, password=args.password)
    except (OSError, pdfsieve.PdfSieveError) as exc:
        print(f"pdfpainter: {exc}", file=sys.stderr)
        return 2
    with doc:
        try:
            pages = parse_pages(args.pages, doc.page_count)
        except ValueError as exc:
            print(f"pdfpainter: {exc}", file=sys.stderr)
            return 2
        pattern = args.output or os.path.splitext(os.path.basename(args.pdf))[0] + "-{page}.png"
        for i in pages:
            info: dict = {}
            img = render(doc.page(i), dpi=args.dpi, info=info, text=not args.no_text)
            name = out_name(pattern, i, len(pages) > 1)
            try:
                img.save(name)
            except (OSError, ValueError) as exc:
                print(f"pdfpainter: could not write {name}: {exc}", file=sys.stderr)
                return 2
            notes = []
            if info.get("undecoded"):
                notes.append(f"{info['undecoded']} image(s) in an unsupported format shown as grey boxes")
            if info.get("skipped_fills"):
                notes.append(f"{info['skipped_fills']} pattern/shading fill(s) left out")
            print(f"{name}  ({img.width} x {img.height})" + (f"  note: {'; '.join(notes)}" if notes else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
