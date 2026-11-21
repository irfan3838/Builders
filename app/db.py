from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def configure(url: str | None = None, **kw) -> async_sessionmaker[AsyncSession]:
    global _engine, _sessionmaker
    _engine = create_async_engine(url or get_settings().database_url, pool_pre_ping=True, **kw)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _sessionmaker


def sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        configure()
    assert _sessionmaker is not None
    return _sessionmaker


def engine() -> AsyncEngine:
    if _engine is None:
        configure()
    assert _engine is not None
    return _engine


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """One transaction; commits on success, rolls back on any exception."""
    async with sessionmaker()() as s:
        async with s.begin():
            yield s
