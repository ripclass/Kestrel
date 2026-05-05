"""EU Consolidated Sanctions List adapter (placeholder).

EU's consolidated list is published behind a credentialed FSF endpoint
(https://webgate.ec.europa.eu/europeaid/fsd/fsf). For v1 the adapter is
a placeholder so the dispatch surface is uniform; live wiring requires
the EU FSF credentials and is a config switch.
"""
from __future__ import annotations

from app.screening.sources.base import ParsedWatchlistEntry

LIST_SOURCE = "EU"
FEED_URL = "https://webgate.ec.europa.eu/europeaid/fsd/fsf"


async def fetch() -> bytes:
    raise NotImplementedError("EU FSF feed requires credentialed access; configure in V2 phase 6.")


def parse(content: bytes) -> list[ParsedWatchlistEntry]:
    raise NotImplementedError("EU FSF parser pending live wiring; see ofac.py for the parser pattern.")
