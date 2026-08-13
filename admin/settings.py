"""Настройки магазина: тексты, кнопки, валюта — без изменения кода."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from filters import IsAdmin
from services import settings as settings_service
from states import AdminSettingsFSM
from utils import add_log, safe_edit

router = Router(name="admin_settings")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

LABELS = {
    "shop_name": "Название магазина",
    "shop_description": "Описание магазина",
    "welcome_text": "Приветственный текст",
    "currency": "Валюта",
    "btn_catalog": "Кнопка «Каталог»",
    "btn_reviews": "Кнопка «Отзывы»",
    "btn_support": "Кнопка «Техподдержка»",
    "btn_profile": "Кнопка «Профиль»",
    "btn_orders": "Кнопка «Мои заказы»",
}


@router.callback_query(F.data == "a_settings")
async def cb_settings(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback.message, "⚙️ Настройки магазина:", reply_markup=kb.admin_settings_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("aset:"))
async def cb_setting_edit(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 1)[1]
    current = await settings_service.get(key)
    await state.set_state(AdminSettingsFSM.entering_value)
    await state.update_data(key=key)
    label = LABELS.get(key, key)
    await callback.message.answer(f"✏️ {label}\n\nТекущее значение:\n{current}\n\nВведите новое значение:")
    await callback.answer()


@router.message(AdminSettingsFSM.entering_value, F.text)
async def process_setting_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    key = data["key"]
    await settings_service.set(key, message.text.strip())
    await add_log("setting_changed", message.from_user.id, {"key": key})
    await state.clear()
    await message.answer("✅ Настройка обновлена.", reply_markup=kb.admin_settings_kb())
