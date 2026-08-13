"""Контакты техподдержки, отображаемые пользователю."""
from __future__ import annotations

from sqlalchemy import select

from database import get_session
from models import SupportContact


async def list_active() -> list[SupportContact]:
    async with get_session() as session:
        stmt = select(SupportContact).where(SupportContact.is_active.is_(True)).order_by(SupportContact.sort_order)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def list_all() -> list[SupportContact]:
    async with get_session() as session:
        result = await session.execute(select(SupportContact).order_by(SupportContact.sort_order))
        return list(result.scalars().all())


async def get_contact(contact_id: int) -> SupportContact | None:
    async with get_session() as session:
        return await session.get(SupportContact, contact_id)


async def add_contact(username: str, label: str | None) -> SupportContact:
    async with get_session() as session:
        contact = SupportContact(username=username.lstrip("@"), label=label)
        session.add(contact)
        await session.commit()
        await session.refresh(contact)
        return contact


async def toggle_contact(contact_id: int) -> None:
    async with get_session() as session:
        contact = await session.get(SupportContact, contact_id)
        if contact:
            contact.is_active = not contact.is_active
            await session.commit()


async def delete_contact(contact_id: int) -> None:
    async with get_session() as session:
        contact = await session.get(SupportContact, contact_id)
        if contact:
            await session.delete(contact)
            await session.commit()
