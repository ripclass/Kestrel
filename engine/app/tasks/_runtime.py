"""Runtime helpers for Celery tasks.

Each scheduled task spins up a fresh async engine + session per invocation
and disposes them on exit. ``app.database.SessionLocal`` is a module-level
async engine bound to the FastAPI process's event loop; reusing it inside
``asyncio.run(...)`` calls from a Celery worker leaks connections across
loops. Using ``NullPool`` per task keeps each scheduled run isolated.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import get_settings

T = TypeVar("T")


async def _with_session(coro_fn: Callable[[AsyncSession], Awaitable[T]]) -> T:
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        future=True,
        echo=False,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with factory() as session:
            return await coro_fn(session)
    finally:
        await engine.dispose()


def run_async(coro_fn: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Open a fresh async session and run ``coro_fn`` to completion."""
    return asyncio.run(_with_session(coro_fn))
