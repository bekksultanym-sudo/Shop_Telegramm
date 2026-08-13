"""
Подключение к PostgreSQL через SQLAlchemy 2.x (async).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import config
from models import Base

engine = create_async_engine(config.database_url, echo=False, pool_pre_ping=True)

SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_models() -> None:
    """Создаёт таблицы, если их ещё нет (для продакшена рекомендуется Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
