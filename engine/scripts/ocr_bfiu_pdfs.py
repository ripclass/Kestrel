"""OCR every BFIU regulatory PDF in REG RULES/ + cached WebFetch downloads.

Pure scaffolding script: render each PDF page via PyMuPDF to a PIL image,
pytesseract → text with eng+ben Bangla bilingual model, concatenate to a
single .ocr.txt file per source PDF in REG RULES/.

Run from anywhere — paths are absolute.
"""
from __future__ import annotations

import io
import pathlib
import sys
import time

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

# Point pytesseract at the Scoop-installed binary
TESSERACT_EXE = pathlib.Path(
    r"C:\Users\User\scoop\apps\tesseract\current\tesseract.exe"
)
if TESSERACT_EXE.exists():
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_EXE)

REG_RULES = pathlib.Path(r"J:\Enso Intelligence\Kestrel\REG RULES")
WEBFETCH_CACHE = pathlib.Path(
    r"C:\Users\User\.claude\projects\J--Enso-Intelligence-Kestrel"
    r"\f06c7da9-d748-40ff-9449-4a170bb58bc9\tool-results"
)

# Map output filename → source PDF path. WebFetch cache filenames are random
# hashes; rename them to something meaningful on the way in.
SOURCES: list[tuple[str, pathlib.Path]] = [
    ("mlpa_2012_bangla_local.ocr.txt", REG_RULES / "mlp2012(2015incorporated).pdf"),
    ("mlpr_2019_local.ocr.txt", REG_RULES / "mlpr_2019_gazzette.pdf"),
    ("mlpa_2012_english.ocr.txt", WEBFETCH_CACHE / "webfetch-1778904932586-tq11lg.pdf"),
    ("circular_22_dissemination.ocr.txt", WEBFETCH_CACHE / "webfetch-1778904969149-yid4t6.pdf"),
    ("circular_24_tbml_cover.ocr.txt", WEBFETCH_CACHE / "webfetch-1778904972949-r1kze2.pdf"),
    ("circular_26_scheduled_banks.ocr.txt", WEBFETCH_CACHE / "webfetch-1778904978429-laags8.pdf"),
    ("tbml_guidelines_2019.ocr.txt", WEBFETCH_CACHE / "webfetch-1778905180225-l6xdjc.pdf"),
    ("tbml_guidelines_2018_draft.ocr.txt", WEBFETCH_CACHE / "webfetch-1778906099867-8obkd4.pdf"),
]

# Render at 2x scale (150 DPI -> 300 DPI effective) so OCR has enough pixel
# density on small body text. Doubles file size in memory but improves accuracy
# substantially on scanned Bangla.
ZOOM = 2.0
MATRIX = fitz.Matrix(ZOOM, ZOOM)
LANG = "eng+ben"
CONFIG = "--psm 6"  # Assume uniform block of text; works well for body pages


def ocr_pdf(src: pathlib.Path, out_path: pathlib.Path) -> tuple[int, int]:
    """Returns (pages_processed, total_chars)."""
    chars = 0
    with fitz.open(src) as doc:
        n = doc.page_count
        with out_path.open("w", encoding="utf-8") as fh:
            for i, page in enumerate(doc, 1):
                pix = page.get_pixmap(matrix=MATRIX, alpha=False)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(img, lang=LANG, config=CONFIG)
                fh.write(f"\n===== PAGE {i}/{n} =====\n")
                fh.write(text)
                chars += len(text)
                print(f"  page {i}/{n}: {len(text):>5} chars", flush=True)
    return n, chars


def main() -> int:
    if not REG_RULES.exists():
        print(f"REG RULES dir missing: {REG_RULES}", file=sys.stderr)
        return 1

    print(f"Tesseract: {TESSERACT_EXE}")
    print(f"Output dir: {REG_RULES}")
    print(f"Lang: {LANG}  zoom: {ZOOM}x  psm: {CONFIG}\n")

    total_pages = 0
    total_chars = 0
    for outname, src in SOURCES:
        if not src.exists():
            print(f"SKIP (missing): {src}")
            continue
        out_path = REG_RULES / outname
        print(f"--- {outname} ({src.stat().st_size:>9,} bytes) ---")
        t0 = time.time()
        try:
            pages, chars = ocr_pdf(src, out_path)
            dt = time.time() - t0
            total_pages += pages
            total_chars += chars
            print(f"  done: {pages} pages, {chars:,} chars in {dt:.1f}s\n")
        except Exception as e:
            print(f"  FAILED: {e}\n")

    print(f"TOTAL: {total_pages} pages, {total_chars:,} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
