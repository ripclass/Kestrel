"""Scheduled demo-bank seed task (V2 phase 2.3).

Runs ``seed.load_demo_bank.apply_pending_orgs`` on the Beat schedule. Picks up
every bank tenant whose ``settings.demo_seed_pending = true`` (set by the
self-serve signup action in ``web/src/app/actions/bank-signup.ts``) and seeds
each one in turn. Each tenant takes ~30-60s for ~10k transactions, so this
task runs every 10 minutes — well-signed-up users typically check the magic
link within that window and land on a populated bank dashboard.

Idempotent: each ``apply_for_org`` call uses deterministic UUIDs and
``ON CONFLICT DO NOTHING`` for the bulk transaction insert. After success the
loader sets ``settings.demo_seed_pending = false`` so the next Beat tick
skips the org.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.tasks.celery_app import celery_app

logger = logging.getLogger("kestrel.tasks.demo_seed")


@celery_app.task(name="app.tasks.demo_seed_tasks.apply_pending")
def apply_pending() -> dict[str, Any]:
    """Beat-driven entrypoint. Imports the loader lazily so the Celery worker
    boot doesn't pull SQLAlchemy session machinery before it's needed."""
    from seed.load_demo_bank import apply_pending_orgs

    results = asyncio.run(apply_pending_orgs())
    completed = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]
    summary = {
        "status": "completed",
        "tenants_seeded": len(completed),
        "tenants_failed": len(failed),
        "tenants": results,
    }
    if failed:
        logger.warning("demo_bank_seed.partial", extra={"summary": summary})
    elif completed:
        logger.info("demo_bank_seed.batch", extra={"summary": summary})
    return summary
