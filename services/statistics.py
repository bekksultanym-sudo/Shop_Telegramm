"""Статистика и доход для админ-панели."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from database import get_session
from models import Order, OrderStatus, User


async def dashboard_stats() -> dict:
    async with get_session() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar_one()

        since = datetime.now(timezone.utc) - timedelta(hours=24)
        active_users = (
            await session.execute(select(func.count(User.id)).where(User.last_active_at >= since))
        ).scalar_one()

        total_orders = (await session.execute(select(func.count(Order.id)))).scalar_one()
        completed_orders = (
            await session.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED))
        ).scalar_one()
        pending_orders = (
            await session.execute(
                select(func.count(Order.id)).where(
                    Order.status.in_(
                        [
                            OrderStatus.NEW,
                            OrderStatus.WAITING_PAYMENT,
                            OrderStatus.PAYMENT_CHECK,
                            OrderStatus.PAID,
                            OrderStatus.PROCESSING,
                        ]
                    )
                )
            )
        ).scalar_one()

        total_sales = await _sum_completed_since(session, None)
        today_sales = await _sum_completed_since(session, datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0))
        week_sales = await _sum_completed_since(session, datetime.now(timezone.utc) - timedelta(days=7))
        month_sales = await _sum_completed_since(session, datetime.now(timezone.utc) - timedelta(days=30))

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "pending_orders": pending_orders,
            "total_sales": total_sales,
            "today_sales": today_sales,
            "week_sales": week_sales,
            "month_sales": month_sales,
        }


async def _sum_completed_since(session, since: datetime | None) -> Decimal:
    stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.status == OrderStatus.COMPLETED)
    if since is not None:
        stmt = stmt.where(Order.updated_at >= since)
    result = await session.execute(stmt)
    return result.scalar_one()


async def revenue_breakdown() -> dict:
    async with get_session() as session:
        today = await _sum_completed_since(session, datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0))
        days7 = await _sum_completed_since(session, datetime.now(timezone.utc) - timedelta(days=7))
        days30 = await _sum_completed_since(session, datetime.now(timezone.utc) - timedelta(days=30))
        all_time = await _sum_completed_since(session, None)
        return {"today": today, "days7": days7, "days30": days30, "all_time": all_time}
