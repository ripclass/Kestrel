"""Watchlist source adapters.

Each adapter exposes ``fetch()`` and ``parse(content: bytes) -> list[ParsedWatchlistEntry]``.
The Beat-driven ingestion task fetches, parses, and upserts to ``watchlist_entries``.

V1 ships parsers + URL contracts. Live ingestion against external endpoints
is a config switch (Render network egress + scheduled Celery task) — by
default the synthetic seed in ``engine/seed/load_watchlist_synthetic.py``
populates a representative dataset that exercises every code path.
"""

from app.screening.sources.base import ParsedWatchlistEntry

__all__ = ["ParsedWatchlistEntry"]
