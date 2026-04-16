"""PDF generation for case packs + placeholder response for other report exports."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.services.case_export import assemble_case_pack

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

# Try to import WeasyPrint at module load. If system deps (Cairo/Pango/GDK)
# aren't available (Windows dev env, Render without native packages), keep the
# rest of the app functional and surface a clear 503 when the route is hit.
try:
    from weasyprint import CSS, HTML  # type: ignore

    _WEASYPRINT_AVAILABLE = True
    _WEASYPRINT_ERROR: str | None = None
except Exception as exc:  # pragma: no cover — depends on host OS
    _WEASYPRINT_AVAILABLE = False
    _WEASYPRINT_ERROR = f"{type(exc).__name__}: {exc}"
    HTML = None  # type: ignore
    CSS = None  # type: ignore


_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _format_iso(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat(sep=" ", timespec="minutes")
    return str(value)


def build_report_export(report_type: str) -> dict[str, str]:
    """Placeholder for national/compliance/trend report exports.

    Real case pack PDFs go through `render_case_pdf` + the /cases/{id}/export.pdf
    endpoint instead. This function kept for the existing /reports/export flow.
    """
    return {
        "report_type": report_type,
        "status": "queued",
        "message": f"{report_type.replace('_', ' ').title()} export generation has been queued.",
        "generated_at": datetime.now(UTC).isoformat(),
    }


async def render_case_pdf(
    session: AsyncSession,
    *,
    case_id: str,
    user: AuthenticatedUser,
) -> bytes:
    """Render a case pack PDF. Returns raw bytes."""
    if not _WEASYPRINT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "PDF generation is unavailable on this host — WeasyPrint could not "
                f"be imported. Underlying error: {_WEASYPRINT_ERROR}"
            ),
        )

    pack = await assemble_case_pack(session, case_id=case_id, user=user)

    # Normalize timestamp fields for the template
    for event in pack.get("timeline", []):
        event["occurred_at"] = _format_iso(event.get("occurred_at"))

    rendered_html = _env.get_template("case_pack.html").render(
        **pack,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )

    css_path = _TEMPLATE_DIR / "case_pack.css"
    return HTML(string=rendered_html).write_pdf(  # type: ignore[no-any-return]
        stylesheets=[CSS(filename=str(css_path))],
    )
