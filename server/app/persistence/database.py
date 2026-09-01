"""Async SQLAlchemy engine, session factory, and FastAPI dependency."""

from collections.abc import AsyncIterator
import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./baby_english.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


class Base(DeclarativeBase):
    """Declarative metadata root used by Alembic."""


engine = create_async_engine(DATABASE_URL)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield one request-scoped database session."""
    async with SessionFactory() as session:
        yield session
