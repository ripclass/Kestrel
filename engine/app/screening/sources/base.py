"""Base contracts for watchlist source adapters."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol


@dataclass(slots=True)
class ParsedWatchlistEntry:
    """Source-agnostic shape produced by every adapter.

    Maps 1:1 to ``models.watchlist.WatchlistEntry``. The ingestion task
    upserts these into Postgres keyed by ``(list_source, primary_name,
    list_version, COALESCE(date_of_birth, '1900-01-01'))``.
    """

    list_source: str
    list_version: str
    entry_type: str  # individual | entity | vessel | aircraft
    primary_name: str
    aliases: list[str] = field(default_factory=list)
    date_of_birth: date | None = None
    nationality: str | None = None
    identifiers: dict[str, Any] = field(default_factory=dict)
    addresses: list[dict[str, Any]] = field(default_factory=list)
    reason: str | None = None
    raw_record: dict[str, Any] = field(default_factory=dict)


class WatchlistSource(Protocol):
    """Adapter contract."""

    list_source: str
    feed_url: str

    async def fetch(self) -> bytes:
        """Download the upstream feed (XML / CSV / JSON)."""

    def parse(self, content: bytes) -> list[ParsedWatchlistEntry]:
        """Parse the feed content into ParsedWatchlistEntry rows."""
