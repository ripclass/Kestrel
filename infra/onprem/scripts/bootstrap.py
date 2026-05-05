#!/usr/bin/env python3
"""Boot-time migration runner for on-prem Kestrel deployments.

Runs every `supabase/migrations/*.sql` in lexicographic order against the
local Postgres reachable via DATABASE_URL_SYNC (or DATABASE_URL with the
asyncpg dialect rewritten to plain libpq). Idempotent: a row in
`supabase_migrations.schema_migrations` is the source of truth — already-
applied migrations are skipped without re-reading the file body. Exits
non-zero on the first failed migration so docker-compose's restart loop
holds the engine container until the DB schema is current.

Usage (from inside the container):
    KESTREL_MIGRATIONS_DIR=/app/supabase/migrations python3 /usr/local/bin/kestrel-bootstrap

The path defaults to /app/supabase/migrations because that's where
Dockerfile.engine copies them; on a developer's host you can override.

This intentionally uses psycopg via the system `psql` CLI rather than
SQLAlchemy. We're running raw migration SQL with a mix of CREATE EXTENSION,
ALTER TYPE, and SECURITY DEFINER functions; psql semantics match what
Supabase ran in production.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

MIGRATIONS_DIR = Path(os.environ.get("KESTREL_MIGRATIONS_DIR", "/app/supabase/migrations"))
ASYNCPG_PREFIX = "postgresql+asyncpg://"
LIBPQ_PREFIX = "postgresql://"


def _resolve_dsn() -> str:
    sync = os.environ.get("DATABASE_URL_SYNC")
    if sync:
        return sync
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        sys.stderr.write("[bootstrap] DATABASE_URL is required\n")
        sys.exit(2)
    if raw.startswith(ASYNCPG_PREFIX):
        return LIBPQ_PREFIX + raw[len(ASYNCPG_PREFIX):]
    return raw


def _wait_for_postgres(dsn: str, *, attempts: int = 30, delay: float = 2.0) -> None:
    parsed = urlparse(dsn)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    db = (parsed.path or "/postgres").lstrip("/")
    for n in range(1, attempts + 1):
        try:
            subprocess.run(
                ["pg_isready", "-h", host, "-p", str(port), "-U", user, "-d", db],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except subprocess.CalledProcessError:
            sys.stderr.write(f"[bootstrap] postgres not ready (attempt {n}/{attempts}); sleeping {delay}s\n")
            time.sleep(delay)
    sys.stderr.write("[bootstrap] postgres never became ready\n")
    sys.exit(3)


def _ensure_migrations_table(dsn: str) -> None:
    sql = """
    CREATE SCHEMA IF NOT EXISTS supabase_migrations;
    CREATE TABLE IF NOT EXISTS supabase_migrations.schema_migrations (
        version text PRIMARY KEY,
        statements text[],
        name text,
        applied_at timestamptz NOT NULL DEFAULT now()
    );
    """
    subprocess.run(
        ["psql", dsn, "-v", "ON_ERROR_STOP=1", "-c", sql],
        check=True,
    )


def _list_applied(dsn: str) -> set[str]:
    out = subprocess.run(
        ["psql", dsn, "-At", "-c", "SELECT version FROM supabase_migrations.schema_migrations ORDER BY version"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {line.strip() for line in out.stdout.splitlines() if line.strip()}


def _version_from_filename(path: Path) -> str:
    # Match Supabase's convention: leading digits before the underscore.
    match = re.match(r"^(\d+)_", path.name)
    if not match:
        return path.stem
    return match.group(1)


def _apply(dsn: str, path: Path, version: str) -> None:
    sys.stderr.write(f"[bootstrap] applying {path.name} (version={version})\n")
    subprocess.run(
        ["psql", dsn, "-v", "ON_ERROR_STOP=1", "-1", "-f", str(path)],
        check=True,
    )
    record = (
        "INSERT INTO supabase_migrations.schema_migrations (version, name) "
        f"VALUES ('{version}', '{path.name.replace(chr(39), chr(39) + chr(39))}') "
        "ON CONFLICT (version) DO NOTHING"
    )
    subprocess.run(["psql", dsn, "-v", "ON_ERROR_STOP=1", "-c", record], check=True)


def main() -> int:
    if not MIGRATIONS_DIR.is_dir():
        sys.stderr.write(f"[bootstrap] migrations dir not found: {MIGRATIONS_DIR}\n")
        return 4

    dsn = _resolve_dsn()
    _wait_for_postgres(dsn)
    _ensure_migrations_table(dsn)

    applied = _list_applied(dsn)
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        sys.stderr.write("[bootstrap] no migration files found\n")
        return 5

    pending = [(path, _version_from_filename(path)) for path in files]
    pending = [(p, v) for (p, v) in pending if v not in applied]

    if not pending:
        sys.stderr.write("[bootstrap] schema is current; nothing to apply\n")
        return 0

    sys.stderr.write(f"[bootstrap] {len(pending)} migration(s) pending\n")
    for path, version in pending:
        try:
            _apply(dsn, path, version)
        except subprocess.CalledProcessError as exc:
            sys.stderr.write(f"[bootstrap] migration {path.name} failed: {exc}\n")
            return 6

    sys.stderr.write("[bootstrap] all migrations applied\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
