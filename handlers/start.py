"""Команда /start и главное меню."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from services import settings as settings_service
from utils import add_log, get_or_create_user, safe_edit

router = Router(name="start")


async def render_main_menu(text_prefix: str = "") -> tuple[str, "kb.InlineKeyboardMarkup"]:
    labels = await settings_service.get_all()
    welcome = await settings_service.get("welcome_text")
    text = f"{text_prefix}{welcome}" if text_prefix else welcome
    return text, kb.main_menu(labels)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await get_or_create_user(message.from_user)
    await add_log("user_start", message.from_user.id)
    text, markup = await render_main_menu()
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text, markup = await render_main_menu()
    await safe_edit(callback.message, text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()
