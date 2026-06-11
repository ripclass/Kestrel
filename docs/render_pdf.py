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

try:
    from playwright.sync_api import sync_playwright  # type: ignore
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


_CSS_TEMPLATE = """
@page {{
    size: A4;
    margin: 26mm 20mm 22mm 20mm;
    @top-left {{
        content: "\\268B  KESTREL";
        font-family: 'IBM Plex Mono', 'Courier New', monospace;
        font-size: 8pt;
        color: #15171c;
        letter-spacing: 0.28em;
        font-weight: 600;
    }}
    @top-right {{
        content: "{doctype}";
        font-family: 'IBM Plex Mono', 'Courier New', monospace;
        font-size: 8pt;
        color: #666;
        letter-spacing: 0.22em;
    }}
    @bottom-right {{
        content: counter(page) " / " counter(pages);
        font-family: 'IBM Plex Mono', 'Courier New', monospace;
        font-size: 9pt;
        color: #666;
    }}
    @bottom-left {{
        content: "{footer}";
        font-family: 'IBM Plex Mono', 'Courier New', monospace;
        font-size: 8pt;
        color: #666;
        letter-spacing: 0.18em;
    }}
}}

* {{ box-sizing: border-box; }}

body {{
    font-family: 'IBM Plex Sans', 'Helvetica Neue', sans-serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #15171c;
}}

h1 {{
    font-size: 22pt;
    font-weight: 600;
    letter-spacing: -0.01em;
    margin: 0 0 4pt 0;
    border-bottom: 1.5pt solid #ff3823;
    padding-bottom: 8pt;
}}

h2 {{
    font-size: 13pt;
    font-weight: 600;
    margin: 18pt 0 6pt 0;
    page-break-after: avoid;
}}

h3 {{
    font-size: 11pt;
    font-weight: 600;
    margin: 12pt 0 4pt 0;
    page-break-after: avoid;
}}

p, ul, ol {{ margin: 0 0 8pt 0; }}

ul, ol {{ padding-left: 18pt; }}

li {{ margin-bottom: 3pt; }}

strong {{ font-weight: 600; }}

code {{
    font-family: 'IBM Plex Mono', 'Courier New', monospace;
    font-size: 9pt;
    background: #f3f3f3;
    padding: 1pt 3pt;
    border-radius: 0;
}}

pre {{
    font-family: 'IBM Plex Mono', 'Courier New', monospace;
    font-size: 9pt;
    background: #f3f3f3;
    padding: 8pt 10pt;
    border-left: 2pt solid #ff3823;
    overflow-x: auto;
    line-height: 1.45;
    margin: 8pt 0;
}}

pre code {{ background: none; padding: 0; }}

blockquote {{
    margin: 0 0 12pt 0;
    padding: 8pt 14pt;
    border-left: 2pt solid #ff3823;
    color: #444;
    font-style: italic;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin: 8pt 0 12pt 0;
    font-size: 9.5pt;
}}

th {{
    text-align: left;
    font-weight: 600;
    padding: 6pt 8pt;
    border-bottom: 1pt solid #15171c;
    background: #f8f8f8;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}

td {{
    padding: 5pt 8pt;
    border-bottom: 0.5pt solid #ddd;
    vertical-align: top;
}}

hr {{
    border: none;
    border-top: 0.5pt solid #ccc;
    margin: 16pt 0;
}}

a {{
    color: #ff3823;
    text-decoration: none;
}}
"""


def _derive_footer(markdown_path: Path, md_text: str) -> str:
    """Pull the first H1 from the document; fall back to the file stem."""
    for line in md_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped.lstrip("# ").strip()
            return f"KESTREL · {title.upper()}"
        if stripped:
            break
    return f"KESTREL · {markdown_path.stem.upper().replace('-', ' ').replace('_', ' ')}"


def _derive_doctype(markdown_path: Path) -> str:
    """Short uppercase doctype tag for the page header (top-right)."""
    stem = markdown_path.stem.upper().replace("-", " ").replace("_", " ")
    # Cap noise — keep doctypes <= ~36 chars so they don't wrap.
    return stem[:42]


def render(markdown_path: Path) -> tuple[Path, Path | None]:
    if not markdown_path.exists():
        raise SystemExit(f"Input not found: {markdown_path}")

    md_text = markdown_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    footer_text = _derive_footer(markdown_path, md_text)
    doctype = _derive_doctype(markdown_path)
    css_styles = _CSS_TEMPLATE.format(footer=footer_text, doctype=doctype)

    # Standalone HTML — embeds the print-stylesheet so browser Print -> PDF
    # uses the same styling as WeasyPrint would.
    full_html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{markdown_path.stem}</title>"
        f"<style>{css_styles}</style></head>"
        f"<body>{html_body}</body></html>"
    )

    html_path = markdown_path.with_suffix(".html")
    html_path.write_text(full_html, encoding="utf-8")

    pdf_path: Path | None = None
    if _WEASYPRINT_AVAILABLE:
        pdf_path = markdown_path.with_suffix(".pdf")
        HTML(string=full_html).write_pdf(
            target=str(pdf_path), stylesheets=[CSS(string=css_styles)]
        )
    elif _PLAYWRIGHT_AVAILABLE:
        # Chromium-headless fallback — works on Windows without GDK/Pango.
        # Chromium doesn't honour CSS @top-*/@bottom-* boxes; use page.pdf()
        # header_template + footer_template instead so every page carries the
        # Kestrel mark + doctype + page counter.
        pdf_path = markdown_path.with_suffix(".pdf")
        header_html = (
            "<div style=\"width:100%;padding:6mm 20mm 0 20mm;"
            "font-family:'IBM Plex Mono','Courier New',monospace;"
            "font-size:8pt;color:#15171c;display:flex;"
            "justify-content:space-between;align-items:center;\">"
            "<span style=\"letter-spacing:0.28em;font-weight:600;\">"
            "<span style=\"color:#ff3823;\">&#x268B;</span>&nbsp;&nbsp;KESTREL</span>"
            f"<span style=\"letter-spacing:0.22em;color:#666;\">{doctype}</span>"
            "</div>"
        )
        footer_html = (
            "<div style=\"width:100%;padding:0 20mm 6mm 20mm;"
            "font-family:'IBM Plex Mono','Courier New',monospace;"
            "font-size:8pt;color:#666;display:flex;"
            "justify-content:space-between;align-items:center;\">"
            f"<span style=\"letter-spacing:0.18em;\">{footer_text}</span>"
            "<span><span class=\"pageNumber\"></span> / "
            "<span class=\"totalPages\"></span></span></div>"
        )
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
            page.pdf(
                path=str(pdf_path),
                format="A4",
                margin={"top": "26mm", "bottom": "22mm", "left": "20mm", "right": "20mm"},
                print_background=True,
                display_header_footer=True,
                header_template=header_html,
                footer_template=footer_html,
            )
            browser.close()

    return html_path, pdf_path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python docs/render_pdf.py <markdown-path>")

    md_path = Path(sys.argv[1])
    html_out, pdf_out = render(md_path)
    print(f"Rendered HTML: {html_out}")
    if pdf_out:
        engine = "WeasyPrint" if _WEASYPRINT_AVAILABLE else "Playwright/Chromium"
        print(f"Rendered PDF:  {pdf_out}  (engine: {engine})")
    else:
        print("PDF skipped: neither WeasyPrint nor Playwright is available.")
        print("Install Playwright with: pip install playwright && playwright install chromium")
        print("Or open the HTML in a browser and File -> Print -> Save as PDF.")


if __name__ == "__main__":
    main()
