"""Способы оплаты (реквизиты) — полностью управляются из админ-панели."""
from __future__ import annotations

from sqlalchemy import select

from database import get_session
from models import PaymentMethod


async def list_methods(only_active: bool = True) -> list[PaymentMethod]:
    async with get_session() as session:
        stmt = select(PaymentMethod).order_by(PaymentMethod.sort_order, PaymentMethod.id)
        if only_active:
            stmt = stmt.where(PaymentMethod.is_active.is_(True))
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_method(method_id: int) -> PaymentMethod | None:
    async with get_session() as session:
        return await session.get(PaymentMethod, method_id)


async def create_method(name: str, details: str, instructions: str | None) -> PaymentMethod:
    async with get_session() as session:
        method = PaymentMethod(name=name, details=details, instructions=instructions)
        session.add(method)
        await session.commit()
        await session.refresh(method)
        return method


async def toggle_method(method_id: int) -> None:
    async with get_session() as session:
        method = await session.get(PaymentMethod, method_id)
        if method:
            method.is_active = not method.is_active
            await session.commit()


async def delete_method(method_id: int) -> None:
    async with get_session() as session:
        method = await session.get(PaymentMethod, method_id)
        if method:
            await session.delete(method)
            await session.commit()
