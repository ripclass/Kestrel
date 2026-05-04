"""Render a markdown doc to standalone HTML, plus PDF if WeasyPrint is available.

Usage:
    python docs/render_pdf.py docs/cross-bank-intelligence.md

Always emits .html (works anywhere, openable in any browser, Print -> PDF works).
Additionally emits .pdf when WeasyPrint can load its native deps. Windows local
installs typically can't load GDK/Pango at runtime; the Render engine container
ships them via apt and renders both fine.

To render on Render (interactive):
    render ssh srv-d7757oidbo4c73e98tlg
    cd /opt/render/project/src && pip install markdown && python docs/render_pdf.py docs/cross-bank-intelligence.md

To render on any Linux box:
    apt install libcairo2 libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0
    pip install weasyprint markdown
    python docs/render_pdf.py docs/cross-bank-intelligence.md
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import markdown
except ImportError as exc:
    raise SystemExit(
        f"Missing dependency: {exc}. Install with: pip install markdown"
    )

try:
    from weasyprint import CSS, HTML  # type: ignore
    _WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    _WEASYPRINT_AVAILABLE = False


CSS_STYLES = """
@page {
    size: A4;
    margin: 22mm 20mm 22mm 20mm;
    @bottom-right {
        content: counter(page) " / " counter(pages);
        font-family: 'IBM Plex Mono', 'Courier New', monospace;
        font-size: 9pt;
        color: #666;
    }
    @bottom-left {
        content: "KESTREL · CROSS-BANK INTELLIGENCE";
        font-family: 'IBM Plex Mono', 'Courier New', monospace;
        font-size: 8pt;
        color: #666;
        letter-spacing: 0.18em;
    }
}

* { box-sizing: border-box; }

body {
    font-family: 'IBM Plex Sans', 'Helvetica Neue', sans-serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #15171c;
}

h1 {
    font-size: 22pt;
    font-weight: 600;
    letter-spacing: -0.01em;
    margin: 0 0 4pt 0;
    border-bottom: 1.5pt solid #ff3823;
    padding-bottom: 8pt;
}

h2 {
    font-size: 13pt;
    font-weight: 600;
    margin: 18pt 0 6pt 0;
    page-break-after: avoid;
}

h3 {
    font-size: 11pt;
    font-weight: 600;
    margin: 12pt 0 4pt 0;
    page-break-after: avoid;
}

p, ul, ol { margin: 0 0 8pt 0; }

ul, ol { padding-left: 18pt; }

li { margin-bottom: 3pt; }

strong { font-weight: 600; }

code {
    font-family: 'IBM Plex Mono', 'Courier New', monospace;
    font-size: 9pt;
    background: #f3f3f3;
    padding: 1pt 3pt;
    border-radius: 0;
}

pre {
    font-family: 'IBM Plex Mono', 'Courier New', monospace;
    font-size: 9pt;
    background: #f3f3f3;
    padding: 8pt 10pt;
    border-left: 2pt solid #ff3823;
    overflow-x: auto;
    line-height: 1.45;
    margin: 8pt 0;
}

pre code { background: none; padding: 0; }

blockquote {
    margin: 0 0 12pt 0;
    padding: 8pt 14pt;
    border-left: 2pt solid #ff3823;
    color: #444;
    font-style: italic;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 8pt 0 12pt 0;
    font-size: 9.5pt;
}

th {
    text-align: left;
    font-weight: 600;
    padding: 6pt 8pt;
    border-bottom: 1pt solid #15171c;
    background: #f8f8f8;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

td {
    padding: 5pt 8pt;
    border-bottom: 0.5pt solid #ddd;
    vertical-align: top;
}

hr {
    border: none;
    border-top: 0.5pt solid #ccc;
    margin: 16pt 0;
}

a {
    color: #ff3823;
    text-decoration: none;
}
"""


def render(markdown_path: Path) -> tuple[Path, Path | None]:
    if not markdown_path.exists():
        raise SystemExit(f"Input not found: {markdown_path}")

    md_text = markdown_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

    # Standalone HTML — embeds the print-stylesheet so browser Print -> PDF
    # uses the same styling as WeasyPrint would.
    full_html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{markdown_path.stem}</title>"
        f"<style>{CSS_STYLES}</style></head>"
        f"<body>{html_body}</body></html>"
    )

    html_path = markdown_path.with_suffix(".html")
    html_path.write_text(full_html, encoding="utf-8")

    pdf_path: Path | None = None
    if _WEASYPRINT_AVAILABLE:
        pdf_path = markdown_path.with_suffix(".pdf")
        HTML(string=full_html).write_pdf(
            target=str(pdf_path), stylesheets=[CSS(string=CSS_STYLES)]
        )

    return html_path, pdf_path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python docs/render_pdf.py <markdown-path>")

    md_path = Path(sys.argv[1])
    html_out, pdf_out = render(md_path)
    print(f"Rendered HTML: {html_out}")
    if pdf_out:
        print(f"Rendered PDF:  {pdf_out}")
    else:
        print("PDF skipped: WeasyPrint native deps not available locally.")
        print("Open the HTML in a browser and File -> Print -> Save as PDF.")


if __name__ == "__main__":
    main()
