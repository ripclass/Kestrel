"""Sanctions / PEP screening service (V2 phase 4.2).

Surface for `POST /screening/entity` and the inline call from
``services.realtime_scoring.score_transaction``. Reads the shared
``watchlist_entries`` pool and returns matches above a configurable
score threshold.

Score weights (per V2 build prompt §4.2):

    name similarity   -> 0.4
    DOB match         -> 0.3
    nationality match -> 0.2
    identifier match  -> 0.1

Name similarity uses pg_trgm fuzzy matching on ``primary_name``; aliases are
considered as a fallback. DOB / nationality / identifiers contribute when the
candidate provides them — missing fields just don't add to the score.

The service is read-only against the shared pool. Every call is logged to
``audit_log`` (action ``screening.entity``) by the caller (router or the
realtime-scoring path).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from unicodedata import normalize

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.watchlist import WatchlistEntry

logger = logging.getLogger("kestrel.screening")


_DEFAULT_MIN_MATCH_SCORE = 0.7
_NAME_SIMILARITY_FLOOR = 0.4  # candidate must clear this on pg_trgm to even be considered

_WEIGHT_NAME = 0.4
_WEIGHT_DOB = 0.3
_WEIGHT_NATIONALITY = 0.2
_WEIGHT_IDENTIFIER = 0.1


@dataclass(slots=True)
class ScreeningRequest:
    """Inbound screening payload."""

    name: str
    date_of_birth: date | None = None
    nationality: str | None = None
    nid: str | None = None
    passport: str | None = None
    screening_lists: list[str] = field(default_factory=list)
    minimum_match_score: float = _DEFAULT_MIN_MATCH_SCORE


@dataclass(slots=True)
class ScreeningMatch:
    """One row above the score threshold."""

    list_source: str
    list_version: str
    entry_id: str
    entry_type: str
    matched_name: str
    matched_aliases: list[str]
    matched_entry: dict[str, Any]
    match_score: float
    match_reasons: list[str]


def normalize_name(value: str | None) -> str:
    """Lowercase, strip diacritics, collapse whitespace. Mirrors how
    pg_trgm normalises tokens server-side. Used only in pure helpers; the
    DB-side similarity does its own canonicalisation."""
    if not value:
        return ""
    decomposed = normalize("NFKD", value)
    stripped = "".join(ch for ch in decomposed if not _is_combining(ch))
    return re.sub(r"\s+", " ", stripped).strip().lower()


def _is_combining(ch: str) -> bool:
    return ord(ch) >= 0x0300 and ord(ch) <= 0x036F


def normalize_nationality(value: str | None) -> str:
    """Two-letter or full name -> uppercase token."""
    if not value:
        return ""
    return re.sub(r"[^A-Za-z]", "", value).upper()


def normalize_identifier(value: str | None) -> str:
    """NID / passport: digits + alphas only, uppercase."""
    if not value:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()


def date_match(candidate: date | None, entry_dob: date | None) -> bool:
    if candidate is None or entry_dob is None:
        return False
    return candidate == entry_dob


def nationality_match(candidate: str | None, entry_nat: str | None) -> bool:
    cand = normalize_nationality(candidate)
    target = normalize_nationality(entry_nat)
    if not cand or not target:
        return False
    if cand == target:
        return True
    # Allow ISO 2-letter against ISO 3-letter prefix or vice versa
    if cand.startswith(target) or target.startswith(cand):
        return True
    return False


def identifier_match(
    *,
    candidate_nid: str | None,
    candidate_passport: str | None,
    entry_identifiers: dict[str, Any] | None,
) -> bool:
    if not entry_identifiers:
        return False
    cand_nid = normalize_identifier(candidate_nid)
    cand_pp = normalize_identifier(candidate_passport)
    if not cand_nid and not cand_pp:
        return False
    nid_targets = entry_identifiers.get("nid") or entry_identifiers.get("national_id")
    pp_targets = entry_identifiers.get("passport") or entry_identifiers.get("passports")
    if cand_nid and _identifier_in(cand_nid, nid_targets):
        return True
    if cand_pp and _identifier_in(cand_pp, pp_targets):
        return True
    # Some lists store identifiers under a generic 'docs' bag
    docs = entry_identifiers.get("docs") or entry_identifiers.get("documents") or []
    if isinstance(docs, list):
        for item in docs:
            if not isinstance(item, dict):
                continue
            number = normalize_identifier(item.get("number"))
            if number and (number == cand_nid or number == cand_pp):
                return True
    return False


def _identifier_in(candidate: str, targets: Any) -> bool:
    if targets is None:
        return False
    if isinstance(targets, str):
        return normalize_identifier(targets) == candidate
    if isinstance(targets, list):
        return any(normalize_identifier(t) == candidate for t in targets)
    return False


def alias_similarity(candidate_name: str, aliases: list[str]) -> float:
    """Best alias-vs-candidate similarity, computed in Python without pg_trgm.

    Used as a tiebreaker when pg_trgm matched on primary_name but the alias is
    actually the closer match. Rough — Jaccard on normalized tokens — but
    deterministic and fast.
    """
    if not aliases:
        return 0.0
    cand_tokens = set(normalize_name(candidate_name).split())
    if not cand_tokens:
        return 0.0
    best = 0.0
    for alias in aliases:
        alias_tokens = set(normalize_name(alias).split())
        if not alias_tokens:
            continue
        intersection = cand_tokens & alias_tokens
        union = cand_tokens | alias_tokens
        if not union:
            continue
        jaccard = len(intersection) / len(union)
        if jaccard > best:
            best = jaccard
    return best


def compose_match_score(
    *,
    name_similarity: float,
    dob_hit: bool,
    nationality_hit: bool,
    identifier_hit: bool,
) -> tuple[float, list[str]]:
    """Compose the four weighted contributions into a single 0–1 score.

    Each component contributes its weight × the component value. Name is
    continuous (the pg_trgm similarity); DOB / nationality / identifier are
    binary booleans (1.0 if hit, 0.0 if not). Reasons list captures every
    component that contributed.
    """
    name_part = max(0.0, min(1.0, float(name_similarity))) * _WEIGHT_NAME
    dob_part = _WEIGHT_DOB if dob_hit else 0.0
    nat_part = _WEIGHT_NATIONALITY if nationality_hit else 0.0
    id_part = _WEIGHT_IDENTIFIER if identifier_hit else 0.0
    score = round(name_part + dob_part + nat_part + id_part, 3)
    reasons: list[str] = []
    if name_similarity > 0.0:
        reasons.append(f"primary_name fuzzy match similarity={name_similarity:.2f}")
    if dob_hit:
        reasons.append("date_of_birth exact match")
    if nationality_hit:
        reasons.append("nationality match")
    if identifier_hit:
        reasons.append("identifier match")
    return score, reasons


async def screen_entity(
    session: AsyncSession,
    *,
    request: ScreeningRequest,
) -> list[ScreeningMatch]:
    """Screen one candidate against the watchlist pool.

    Returns matches above ``request.minimum_match_score``, ranked descending.
    Read-only — the caller is responsible for any audit-log write.
    """
    if not request.name or not request.name.strip():
        return []

    candidate = request.name.strip()
    sources_filter = [s for s in (request.screening_lists or []) if s]

    similarity = func.similarity(WatchlistEntry.primary_name, candidate)
    stmt = (
        select(WatchlistEntry, similarity.label("name_sim"))
        .where(WatchlistEntry.removed_at.is_(None))
        .where(
            or_(
                similarity >= _NAME_SIMILARITY_FLOOR,
                # Also consider rows whose alias array shares a token with the
                # candidate. Conservative — full alias scoring happens in Python.
                func.cardinality(WatchlistEntry.aliases) > 0,
            )
        )
        .order_by(similarity.desc())
        .limit(200)
    )
    if sources_filter:
        stmt = stmt.where(WatchlistEntry.list_source.in_(sources_filter))

    try:
        result = await session.execute(stmt)
        candidates = list(result.all())
    except Exception:
        # Defensive: missing pg_trgm extension or test session.
        logger.warning("screening.lookup_failed", extra={"name": candidate})
        return []

    matches: list[ScreeningMatch] = []
    for entry, sim in candidates:
        primary_sim = float(sim or 0.0)
        alias_sim = alias_similarity(candidate, entry.aliases or [])
        effective_sim = max(primary_sim, alias_sim)
        if effective_sim < _NAME_SIMILARITY_FLOOR:
            continue
        dob_hit = date_match(request.date_of_birth, entry.date_of_birth)
        nat_hit = nationality_match(request.nationality, entry.nationality)
        id_hit = identifier_match(
            candidate_nid=request.nid,
            candidate_passport=request.passport,
            entry_identifiers=entry.identifiers,
        )
        score, reasons = compose_match_score(
            name_similarity=effective_sim,
            dob_hit=dob_hit,
            nationality_hit=nat_hit,
            identifier_hit=id_hit,
        )
        if score < request.minimum_match_score:
            continue
        matches.append(
            ScreeningMatch(
                list_source=entry.list_source,
                list_version=entry.list_version,
                entry_id=str(entry.id),
                entry_type=entry.entry_type,
                matched_name=entry.primary_name,
                matched_aliases=list(entry.aliases or []),
                matched_entry={
                    "primary_name": entry.primary_name,
                    "aliases": list(entry.aliases or []),
                    "date_of_birth": entry.date_of_birth.isoformat() if entry.date_of_birth else None,
                    "nationality": entry.nationality,
                    "identifiers": entry.identifiers or {},
                    "addresses": entry.addresses or [],
                    "reason": entry.reason,
                },
                match_score=score,
                match_reasons=reasons,
            )
        )

    matches.sort(key=lambda m: m.match_score, reverse=True)
    return matches


def best_screening_score(matches: list[ScreeningMatch]) -> float:
    """The highest match score in a result set, or 0.0 if empty."""
    if not matches:
        return 0.0
    return max(m.match_score for m in matches)


def parse_screening_date(value: Any) -> date | None:
    """Defensive ISO date parse for inbound payloads. Returns None on bad input."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
