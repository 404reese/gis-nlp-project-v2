"""Async SQLAlchemy engines for the PostGIS spatial database.

Two engines:
- `engine`          — owner role, full access (used by ETL-facing reads and app queries).
- `engine_readonly` — the role LLM-generated SQL executes as (defense-in-depth, §5.5).

Both are lazily created so importing this module never forces a DB connection
(the app must still boot if Postgres/Docker is down; endpoints report that instead).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings

_engine: AsyncEngine | None = None
_engine_readonly: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
        )
    return _engine


def get_engine_readonly() -> AsyncEngine:
    global _engine_readonly
    if _engine_readonly is None:
        _engine_readonly = create_async_engine(
            settings.DATABASE_URL_READONLY,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            # Hard ceiling so a runaway LLM query can't hang a connection forever.
            connect_args={"server_settings": {"statement_timeout": "15000"}},
        )
    return _engine_readonly


async def dispose_engines() -> None:
    global _engine, _engine_readonly
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    if _engine_readonly is not None:
        await _engine_readonly.dispose()
        _engine_readonly = None
