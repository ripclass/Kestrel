"""Sanctions / PEP / adverse-media screening (V2 phase 4).

Public sources of truth for the watchlists; each adapter under
``sources/`` parses one upstream format into ``ParsedWatchlistEntry``.
The ingestion task in ``app.tasks.screening_tasks`` orchestrates them.
"""
