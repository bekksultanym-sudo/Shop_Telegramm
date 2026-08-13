"""Пользователи: список, карточка, блокировка/разблокировка."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from filters import IsAdmin
from services import users as users_service
from states import AdminBanFSM
from utils import add_log, format_price, safe_edit

router = Router(name="admin_users")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "a_users")
async def cb_users(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_users_page(callback, page=0)


@router.callback_query(F.data.startswith("ausers:"))
async def cb_users_page(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":")[1])
    await _show_users_page(callback, page)


async def _show_users_page(callback: CallbackQuery, page: int) -> None:
    users, total_pages = await users_service.list_users(page)
    total = await users_service.count_all()
    active_24h = await users_service.count_active_since(24)
    text = f"👥 Пользователи (всего: {total}, активных за 24ч: {active_24h}):"
    await safe_edit(callback.message, text, reply_markup=kb.admin_users_list_kb(users, page, total_pages))
    await callback.answer()


@router.callback_query(F.data.startswith("auser:"))
async def cb_user_detail(callback: CallbackQuery) -> None:
    tg_id = int(callback.data.split(":")[1])
    user = await users_service.get_user_by_tg_id(tg_id)
    if user is None:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    stats = await users_service.get_user_stats(tg_id)
    spent_str = await format_price(stats.get("total_spent", 0))
    status = "🚫 заблокирован" if user.is_banned else "✅ активен"
    text = f"👤 Пользователь\n\nID: <code>{user.tg_id}</code>\n"
    if user.username:
        text += f"Username: @{user.username}\n"
    text += (
        f"Имя: {user.full_name or '—'}\n"
        f"Первый вход: {user.created_at.strftime('%d.%m.%Y')}\n"
        f"Последняя активность: {user.last_active_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"Заказов: {stats.get('orders_count', 0)}\n"
        f"Сумма покупок: {spent_str}\n"
        f"Статус: {status}"
    )
    if user.is_banned and user.ban_reason:
        text += f"\nПричина блокировки: {user.ban_reason}"
    await safe_edit(callback.message, text, reply_markup=kb.admin_user_detail_kb(user))
    await callback.answer()


@router.callback_query(F.data.startswith("auser_ban:"))
async def cb_user_ban_start(callback: CallbackQuery, state: FSMContext) -> None:
    tg_id = int(callback.data.split(":")[1])
    await state.set_state(AdminBanFSM.entering_reason)
    await state.update_data(tg_id=tg_id)
    await callback.message.answer("Укажите причину блокировки (или «-»):")
    await callback.answer()


@router.message(AdminBanFSM.entering_reason, F.text)
async def process_ban_reason(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    reason = None if message.text.strip() == "-" else message.text.strip()
    await users_service.ban_user(data["tg_id"], reason)
    await add_log("user_banned", message.from_user.id, {"tg_id": data["tg_id"], "reason": reason})
    await state.clear()
    user = await users_service.get_user_by_tg_id(data["tg_id"])
    await message.answer(f"🚫 Пользователь {data['tg_id']} заблокирован.", reply_markup=kb.admin_user_detail_kb(user))


@router.callback_query(F.data.startswith("auser_unban:"))
async def cb_user_unban(callback: CallbackQuery) -> None:
    tg_id = int(callback.data.split(":")[1])
    await users_service.unban_user(tg_id)
    await add_log("user_unbanned", callback.from_user.id, {"tg_id": tg_id})
    await callback.answer("Пользователь разблокирован")
    await cb_user_detail(callback)
