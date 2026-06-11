#!/usr/bin/env python3
"""Apply named Supabase migrations from a cloud engine instance.

Cloud companion to infra/onprem/scripts/bootstrap.py for environments where
psql is unavailable but the engine's own DATABASE_URL + asyncpg are (e.g. a
Render one-off job):

    render jobs create <engine-service-id> \
        --start-command "python scripts/apply_migrations.py 029_bank_signup_requests.sql"

Deliberately takes EXPLICIT migration filenames rather than auto-applying
everything missing from supabase_migrations.schema_migrations — historical
rows were recorded through several tools and version-string formats, so an
auto mode could mistake an applied migration for a pending one and try to
re-apply the whole chain. Each named file runs in its own transaction and is
recorded with the same (version = leading digits, name = filename) convention
the on-prem bootstrap uses.

    python scripts/apply_migrations.py --list   # applied versions + available files
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

import asyncpg

ASYNCPG_PREFIX = "postgresql+asyncpg://"
LIBPQ_PREFIX = "postgresql://"


def _resolve_dsn() -> str:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        sys.stderr.write("[migrate] DATABASE_URL is required\n")
        sys.exit(2)
    if raw.startswith(ASYNCPG_PREFIX):
        return LIBPQ_PREFIX + raw[len(ASYNCPG_PREFIX):]
    return raw


def resolve_migrations_dir() -> Path:
    """supabase/migrations relative to the repo root, wherever we run from.

    Render sets rootDir to engine/ but clones the full repo, so the
    migrations live one level up. Local runs from the repo root or engine/
    both work; KESTREL_MIGRATIONS_DIR overrides everything.
    """
    override = os.environ.get("KESTREL_MIGRATIONS_DIR")
    if override:
        return Path(override)
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "supabase" / "migrations",  # <repo>/engine/scripts -> <repo>/supabase
        Path.cwd() / "supabase" / "migrations",
        Path.cwd().parent / "supabase" / "migrations",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[0]


def version_from_filename(name: str) -> str:
    """Match Supabase's convention: leading digits before the underscore."""
    match = re.match(r"^(\d+)_", name)
    if not match:
        return Path(name).stem
    return match.group(1)


async def _connect(dsn: str) -> asyncpg.Connection:
    try:
        return await asyncpg.connect(dsn=dsn)
    except Exception:
        return await asyncpg.connect(dsn=dsn, ssl="require")


async def _list(conn: asyncpg.Connection, migrations_dir: Path) -> None:
    rows = await conn.fetch(
        "SELECT version, name FROM supabase_migrations.schema_migrations ORDER BY version"
    )
    print(f"[migrate] {len(rows)} recorded migration(s):")
    for row in rows:
        print(f"  {row['version']}  {row['name'] or ''}")
    files = sorted(migrations_dir.glob("*.sql"))
    print(f"[migrate] {len(files)} file(s) in {migrations_dir}:")
    for path in files:
        print(f"  {path.name}")


async def _apply_one(conn: asyncpg.Connection, path: Path) -> None:
    version = version_from_filename(path.name)
    already = await conn.fetchval(
        "SELECT 1 FROM supabase_migrations.schema_migrations WHERE version = $1",
        version,
    )
    if already:
        print(f"[migrate] {path.name} (version={version}) already recorded — skipping")
        return
    sql = path.read_text(encoding="utf-8")
    print(f"[migrate] applying {path.name} (version={version})")
    async with conn.transaction():
        await conn.execute(sql)
        await conn.execute(
            "INSERT INTO supabase_migrations.schema_migrations (version, name) "
            "VALUES ($1, $2) ON CONFLICT (version) DO NOTHING",
            version,
            path.name,
        )
    print(f"[migrate] {path.name} applied + recorded")


async def main(argv: list[str]) -> int:
    migrations_dir = resolve_migrations_dir()
    if not migrations_dir.is_dir():
        sys.stderr.write(f"[migrate] migrations dir not found: {migrations_dir}\n")
        return 4

    conn = await _connect(_resolve_dsn())
    try:
        if argv == ["--list"]:
            await _list(conn, migrations_dir)
            return 0
        if not argv:
            sys.stderr.write(
                "[migrate] pass explicit migration filenames (or --list); "
                "auto-apply is intentionally unsupported\n"
            )
            return 5
        for name in argv:
            path = migrations_dir / Path(name).name
            if not path.is_file():
                sys.stderr.write(f"[migrate] not found: {path}\n")
                return 6
            await _apply_one(conn, path)
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
