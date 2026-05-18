"""PDF generation for case packs and operator briefing packs."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.services.case_export import assemble_case_pack
from app.services.compliance import get_scorecard
from app.services.reporting import build_overview, build_trend_series
from app.services.statistics import build_operational_statistics

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
    """Lightweight metadata response. Used when the caller does not need
    bytes (or when WeasyPrint is unavailable on the host).
    """
    return {
        "report_type": report_type,
        "status": "queued",
        "message": f"{report_type.replace('_', ' ').title()} export generation has been queued.",
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _composite_band(score: int) -> str:
    if score >= 90:
        return "leading"
    if score >= 70:
        return "neutral"
    if score >= 50:
        return "watchlist"
    return "attention"


async def _gather_pack_payload(
    session: AsyncSession,
    *,
    report_type: str,
    user: AuthenticatedUser,
) -> dict[str, Any]:
    """Compose the Jinja context for a report pack.

    Each pack-type emphasises different sections; all draw from existing
    services so there is one source of truth and no special-case data.
    """
    operator_name = getattr(user, "email", "Operator")
    operator_org = getattr(user, "org_name", None) or "Operator organisation"
    classification = "CONFIDENTIAL"

    pack_meta = {
        "pack_type": report_type,
        "pack_title": "National briefing pack",
        "pack_eyebrow": "Kestrel · Command pack",
        "pack_subtitle": "Composed from live platform data.",
        "classification": classification,
        "operator_name": operator_name,
        "operator_org": operator_org,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    }

    payload: dict[str, Any] = {**pack_meta}

    if report_type == "national":
        payload["pack_title"] = "National briefing pack"
        payload["pack_subtitle"] = (
            "Director-level command view — typologies, channels, and institutions "
            "requiring attention."
        )
        overview = await build_overview(session, user=user)
        payload["national_summary"] = {
            "intro": overview.headline,
            "kpis": [
                {"label": k.label, "value": k.value, "note": k.delta_label or ""}
                for k in overview.stats
            ],
        }
        payload["typology_summary"] = {
            "window_label": "current period",
            "items": [
                {
                    "label": f"#{i+1:02d}",
                    "detail": entry,
                }
                for i, entry in enumerate(overview.operational[:5])
            ],
        }
        scorecard = await get_scorecard(session)
        payload["compliance_rows"] = [
            {
                "bank_name": row.org_name,
                "timeliness": row.submission_timeliness,
                "conversion": row.alert_conversion,
                "coverage": row.peer_coverage,
                "composite": row.score,
                "band": _composite_band(row.score),
            }
            for row in scorecard.banks
        ]

    elif report_type == "compliance":
        payload["pack_title"] = "Compliance scorecard"
        payload["pack_subtitle"] = (
            "Bank-by-bank readiness ranking — Timeliness × Conversion × Coverage."
        )
        scorecard = await get_scorecard(session)
        payload["compliance_rows"] = [
            {
                "bank_name": row.org_name,
                "timeliness": row.submission_timeliness,
                "conversion": row.alert_conversion,
                "coverage": row.peer_coverage,
                "composite": row.score,
                "band": _composite_band(row.score),
            }
            for row in scorecard.banks
        ]

    elif report_type == "trends":
        payload["pack_title"] = "Trend analysis digest"
        payload["pack_subtitle"] = (
            "Alert volume + STR filings over the last 24 months."
        )
        trend = await build_trend_series(session)
        rows = []
        for point in trend.series:
            alerts = point.alerts or 0
            strs = point.str_reports or 0
            conversion_pct = round((strs / alerts) * 100, 1) if alerts else 0.0
            rows.append({
                "period": point.month,
                "alerts": alerts,
                "strs": strs,
                "conversion_pct": conversion_pct,
            })
        payload["trend_rows"] = {
            "window_label": "trailing months",
            "rows": rows,
        }
        try:
            stats = await build_operational_statistics(session)
            rows_stats = []
            # build_operational_statistics returns a dict in current shape
            if isinstance(stats, dict):
                for k, v in stats.items():
                    if isinstance(v, (int, float, str)):
                        rows_stats.append({"label": k.replace("_", " ").title(), "value": v})
            payload["statistics"] = {
                "window_label": "to date",
                "rows": rows_stats[:12],
            }
        except Exception:  # noqa: BLE001 — statistics are nice-to-have on the trend pack
            pass

    else:
        payload["pack_title"] = f"{report_type.replace('_', ' ').title()} pack"
        payload["pack_subtitle"] = (
            "This pack type is not yet wired to a data composer; "
            "see /admin/schedules for the canonical Beat-task report."
        )

    return payload


async def render_report_pack_pdf(
    session: AsyncSession,
    *,
    report_type: str,
    user: AuthenticatedUser,
) -> bytes:
    """Render a national / compliance / trend briefing pack as PDF bytes."""
    if not _WEASYPRINT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "PDF generation is unavailable on this host — WeasyPrint could "
                f"not be imported. Underlying error: {_WEASYPRINT_ERROR}"
            ),
        )

    context = await _gather_pack_payload(session, report_type=report_type, user=user)
    rendered_html = _env.get_template("report_pack.html").render(**context)
    css_path = _TEMPLATE_DIR / "report_pack.css"
    return HTML(string=rendered_html).write_pdf(  # type: ignore[no-any-return]
        stylesheets=[CSS(filename=str(css_path))],
    )


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
