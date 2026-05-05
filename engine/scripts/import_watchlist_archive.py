"""Air-gapped watchlist import (V3 phase 6.4).

Operators in air-gapped customer environments can't run the live Beat
ingestion (no internet egress). Instead they download the OFAC SDN /
UN consolidated / UK OFSI feeds onto a USB stick, ship it onto the
customer site, and run::

    python -m scripts.import_watchlist_archive --archive /var/lib/kestrel/watchlist

The directory is expected to contain one or more of:

    sdn.xml             # OFAC
    consolidated.xml    # UN
    UK-Sanctions-List.csv  # UK OFSI

Filename matching is case-insensitive and tolerant of arbitrary
prefixes/suffixes (e.g. ``ofac-2026-05-05.sdn.xml``). The script:

1. Walks the archive directory.
2. Picks the right parser per file via filename heuristics.
3. Hands the parsed rows to the same upsert path the Beat task uses
   (``screening_tasks._upsert_batch``) so the deterministic PK and
   ``ON CONFLICT DO NOTHING`` semantics are identical.

The script is intentionally engine-agnostic about HOW the customer
gets the file in. They might unzip from USB, NFS-mount, or `scp` from
a jumphost. We just consume the directory.

Idempotent: running twice in a row is a no-op for unchanged feeds.
``--dry-run`` parses + reports counts without touching the DB.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Callable

from app.screening.sources import ofac, uk_ofsi, un
from app.screening.sources.base import ParsedWatchlistEntry
from app.tasks.screening_tasks import _upsert_batch as upsert_batch

logger = logging.getLogger("kestrel.scripts.import_watchlist_archive")

# Filename predicate -> (parser, list_source) — matched in order.
_HANDLERS: list[tuple[Callable[[str], bool], Any, str]] = [
    (lambda name: "sdn" in name and name.endswith(".xml"), ofac, "OFAC"),
    (lambda name: "consolidated" in name and name.endswith(".xml"), un, "UN"),
    (lambda name: name.endswith(".csv") and ("uk" in name or "ofsi" in name or "sanctions" in name), uk_ofsi, "UK_OFSI"),
]


def _classify(path: Path) -> tuple[Any, str] | None:
    name = path.name.lower()
    for predicate, parser, list_source in _HANDLERS:
        if predicate(name):
            return parser, list_source
    return None


def _parse_one(path: Path) -> tuple[str, list[ParsedWatchlistEntry]]:
    classified = _classify(path)
    if classified is None:
        raise ValueError(f"unrecognised filename {path.name}")
    parser, list_source = classified
    content = path.read_bytes()
    rows = parser.parse(content)
    return list_source, rows


async def _apply(rows: list[ParsedWatchlistEntry]) -> int:
    return await upsert_batch(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import an offline watchlist archive into Kestrel.")
    parser.add_argument(
        "--archive",
        required=True,
        help="Directory containing OFAC/UN/UK feed files (XML/CSV).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report counts; do not touch the database.",
    )
    parser.add_argument(
        "--verbose", "-v", action="count", default=0, help="Increase log verbosity (can be repeated)."
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING - 10 * min(args.verbose, 2),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    archive_dir = Path(args.archive)
    if not archive_dir.is_dir():
        sys.stderr.write(f"--archive must point at a directory; got {archive_dir}\n")
        return 2

    files = sorted(p for p in archive_dir.iterdir() if p.is_file())
    if not files:
        sys.stderr.write(f"no files in {archive_dir}\n")
        return 3

    summary: dict[str, dict[str, int]] = {}
    grouped: dict[str, list[ParsedWatchlistEntry]] = {}

    for path in files:
        try:
            list_source, rows = _parse_one(path)
        except ValueError as exc:
            logger.warning("skipping unrecognised file: %s", exc)
            continue
        except Exception as exc:  # noqa: BLE001 — operator-facing report
            logger.error("parse failure in %s: %s", path, exc)
            return 4
        grouped.setdefault(list_source, []).extend(rows)
        bucket = summary.setdefault(list_source, {"files": 0, "rows": 0, "ingested": 0})
        bucket["files"] += 1
        bucket["rows"] += len(rows)

    if not grouped:
        sys.stderr.write("no recognisable feed files found; expected sdn.xml / consolidated.xml / UK-Sanctions-List.csv\n")
        return 5

    if args.dry_run:
        for list_source, stats in summary.items():
            print(f"{list_source}: parsed {stats['rows']} rows from {stats['files']} file(s) (dry-run)")
        return 0

    for list_source, rows in grouped.items():
        ingested = asyncio.run(_apply(rows))
        summary[list_source]["ingested"] = ingested

    for list_source, stats in summary.items():
        print(f"{list_source}: ingested {stats['ingested']}/{stats['rows']} rows from {stats['files']} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
