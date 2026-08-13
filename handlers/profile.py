"""Раздел «Профиль»."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

import keyboards as kb
from services import users as users_service
from utils import format_price, get_or_create_user, safe_edit

router = Router(name="profile")


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user)
    stats = await users_service.get_user_stats(user.tg_id)
    spent_str = await format_price(stats.get("total_spent", 0))

    text = f"👤 <b>Профиль</b>\n\nID: <code>{user.tg_id}</code>\n"
    if user.username:
        text += f"Username: @{user.username}\n"
    text += (
        f"\n📅 С нами с: {user.created_at.strftime('%d.%m.%Y')}\n"
        f"📦 Заказов: {stats.get('orders_count', 0)}\n"
        f"💰 Всего потрачено: {spent_str}"
    )
    await safe_edit(callback.message, text, reply_markup=kb.back_home_kb())
    await callback.answer()
