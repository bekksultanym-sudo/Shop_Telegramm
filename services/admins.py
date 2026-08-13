"""Управление списком администраторов и их ролями."""
from __future__ import annotations

from sqlalchemy import select

from database import get_session
from models import Admin, AdminRole


async def list_admins() -> list[Admin]:
    async with get_session() as session:
        result = await session.execute(select(Admin).order_by(Admin.created_at))
        return list(result.scalars().all())


async def list_admin_tg_ids() -> list[int]:
    async with get_session() as session:
        result = await session.execute(select(Admin.tg_id))
        return [row[0] for row in result.all()]


async def add_admin(tg_id: int, username: str | None, role: AdminRole, added_by: int | None) -> Admin:
    async with get_session() as session:
        result = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
        existing = result.scalar_one_or_none()
        if existing:
            existing.role = role
            await session.commit()
            await session.refresh(existing)
            return existing
        admin = Admin(tg_id=tg_id, username=username, role=role, added_by=added_by)
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return admin


async def remove_admin(tg_id: int) -> None:
    async with get_session() as session:
        result = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
        admin = result.scalar_one_or_none()
        if admin:
            await session.delete(admin)
            await session.commit()


async def get_admin_by_tg_id(tg_id: int) -> Admin | None:
    async with get_session() as session:
        result = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
        return result.scalar_one_or_none()
