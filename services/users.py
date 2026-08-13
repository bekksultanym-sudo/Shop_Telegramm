"""Управление пользователями: список, бан/разбан, статистика по покупкам."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from database import get_session
from models import Order, OrderStatus, User


async def list_users(page: int = 0, per_page: int = 10) -> tuple[list[User], int]:
    async with get_session() as session:
        total = (await session.execute(select(func.count(User.id)))).scalar_one()
        total_pages = max(1, (total + per_page - 1) // per_page)
        stmt = select(User).order_by(User.created_at.desc()).offset(page * per_page).limit(per_page)
        result = await session.execute(stmt)
        return list(result.scalars().all()), total_pages


async def get_user_by_tg_id(tg_id: int) -> User | None:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()


async def get_user_stats(tg_id: int) -> dict:
    async with get_session() as session:
        user_result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = user_result.scalar_one_or_none()
        if not user:
            return {}
        orders_count = (
            await session.execute(select(func.count(Order.id)).where(Order.user_id == user.id))
        ).scalar_one()
        spent = (
            await session.execute(
                select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                    Order.user_id == user.id, Order.status == OrderStatus.COMPLETED
                )
            )
        ).scalar_one()
        return {"orders_count": orders_count, "total_spent": spent}


async def ban_user(tg_id: int, reason: str | None) -> None:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_banned = True
            user.ban_reason = reason
            await session.commit()


async def unban_user(tg_id: int) -> None:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_banned = False
            user.ban_reason = None
            await session.commit()


async def count_active_since(hours: int = 24) -> int:
    async with get_session() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await session.execute(select(func.count(User.id)).where(User.last_active_at >= since))
        return result.scalar_one()


async def count_all() -> int:
    async with get_session() as session:
        result = await session.execute(select(func.count(User.id)))
        return result.scalar_one()


async def list_all_tg_ids(exclude_banned: bool = True) -> list[int]:
    async with get_session() as session:
        stmt = select(User.tg_id)
        if exclude_banned:
            stmt = stmt.where(User.is_banned.is_(False))
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]
