"""Adverse-media screening adapter (V2 phase 4.3).

V1 ships a stub. ComplyAdvantage is the obvious paid provider; the adapter
pattern lets us turn it on per-customer without code changes — set
``COMPLYADVANTAGE_API_KEY`` on Render and the engine routes inbound calls
to ComplyAdvantage's `/v2/searches` endpoint. Without the key, every call
returns an empty result set and a `provider=stub` evidence marker.

The shape mirrors ``services.screening.ScreeningMatch`` so the realtime
scoring path can fold adverse-media hits into the same reasons array.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger("kestrel.adverse_media")

_SEARCH_TIMEOUT_SECONDS = 5.0
_BASE_PATH = "/v2/searches"


@dataclass(slots=True)
class AdverseMediaQuery:
    name: str
    nationality: str | None = None
    fuzziness: float = 0.5
    types: list[str] = field(default_factory=lambda: ["adverse-media"])


@dataclass(slots=True)
class AdverseMediaHit:
    name: str
    snippet: str
    url: str | None
    published_at: str | None
    score: float
    raw: dict[str, Any]


def is_provider_configured() -> bool:
    settings = get_settings()
    return bool(settings.complyadvantage_api_key)


async def search_adverse_media(query: AdverseMediaQuery) -> list[AdverseMediaHit]:
    """Run an adverse-media search.

    Returns an empty list when the provider is not configured. When configured,
    posts to ComplyAdvantage's `/v2/searches` and adapts the response. Network
    failures degrade gracefully to an empty result with a logged warning —
    we never let an upstream outage block scoring.
    """
    settings = get_settings()
    if not settings.complyadvantage_api_key:
        logger.info(
            "adverse_media.skipped",
            extra={"reason": "provider_not_configured", "query_name": query.name},
        )
        return []

    payload = {
        "search_term": query.name,
        "fuzziness": query.fuzziness,
        "filters": {"types": query.types},
        "share_url": False,
    }
    if query.nationality:
        payload["filters"]["country_codes"] = [query.nationality]

    headers = {
        "Authorization": f"Token {settings.complyadvantage_api_key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.complyadvantage_base_url.rstrip('/')}{_BASE_PATH}"

    try:
        async with httpx.AsyncClient(timeout=_SEARCH_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            logger.warning(
                "adverse_media.upstream_error",
                extra={"status_code": response.status_code, "query_name": query.name},
            )
            return []
        body = response.json()
    except httpx.HTTPError as exc:
        logger.warning(
            "adverse_media.network_error",
            extra={"error_type": type(exc).__name__, "query_name": query.name},
        )
        return []
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "adverse_media.unexpected_error",
            extra={"error_type": type(exc).__name__, "query_name": query.name},
        )
        return []

    return _parse_complyadvantage_response(body)


def _parse_complyadvantage_response(body: dict[str, Any]) -> list[AdverseMediaHit]:
    """Map ComplyAdvantage's search response into our AdverseMediaHit shape.

    ComplyAdvantage nests hits under ``data.hits`` with an ``adverse_media``
    array of articles per hit. We flatten one ``AdverseMediaHit`` per article
    so the realtime scoring path can score on a per-article basis.
    """
    data = (body or {}).get("data") or {}
    hits = data.get("hits") or []
    flattened: list[AdverseMediaHit] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        articles = (hit.get("doc") or {}).get("media") or hit.get("adverse_media") or []
        if not isinstance(articles, list):
            continue
        score = float(hit.get("match_score") or 0.0) / 100.0 if hit.get("match_score") else 0.5
        for article in articles:
            if not isinstance(article, dict):
                continue
            flattened.append(
                AdverseMediaHit(
                    name=str((hit.get("doc") or {}).get("name") or hit.get("name") or ""),
                    snippet=str(article.get("snippet") or article.get("title") or ""),
                    url=article.get("url"),
                    published_at=article.get("date"),
                    score=score,
                    raw=article,
                )
            )
    return flattened
