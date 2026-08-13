"""Точка входа в админ-панель: команда /admin и главное меню."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from filters import is_admin
from utils import safe_edit

router = Router(name="admin_dashboard")

ACCESS_DENIED = "❌ Доступ запрещён."


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        await message.answer(ACCESS_DENIED)
        return
    await state.clear()
    await message.answer("👑 Админ-панель\n\nВыберите раздел:", reply_markup=kb.admin_main_menu())


@router.callback_query(F.data == "admin_home")
async def cb_admin_home(callback: CallbackQuery, state: FSMContext) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer(ACCESS_DENIED, show_alert=True)
        return
    await state.clear()
    await safe_edit(callback.message, "👑 Админ-панель\n\nВыберите раздел:", reply_markup=kb.admin_main_menu())
    await callback.answer()
