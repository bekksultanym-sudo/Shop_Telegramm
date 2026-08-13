"""Фильтры доступа: проверка администратора, проверка бана."""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database import get_session
from models import Admin, AdminRole, User

ROLE_WEIGHT = {
    AdminRole.SUPPORT: 1,
    AdminRole.ADMIN: 2,
    AdminRole.SUPER_ADMIN: 3,
}


async def get_admin(tg_id: int) -> Admin | None:
    async with get_session() as session:
        result = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
        return result.scalar_one_or_none()


async def is_admin(tg_id: int) -> bool:
    return await get_admin(tg_id) is not None


async def has_role(tg_id: int, minimum: AdminRole) -> bool:
    admin = await get_admin(tg_id)
    if admin is None:
        return False
    return ROLE_WEIGHT[admin.role] >= ROLE_WEIGHT[minimum]


async def is_banned(tg_id: int) -> bool:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        return bool(user and user.is_banned)


class IsAdmin(BaseFilter):
    """Пропускает событие, только если отправитель — администратор бота.

    Для callback_query дополнительно отправляет всплывающее уведомление
    «Доступ запрещён», чтобы кнопка не выглядела «мёртвой».
    """

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        if user is None:
            return False
        if await is_admin(user.id):
            return True
        if isinstance(event, CallbackQuery):
            await event.answer("❌ Доступ запрещён.", show_alert=True)
        else:
            await event.answer("❌ Доступ запрещён.")
        return False
