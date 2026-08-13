"""Раздел «Техподдержка»."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

import keyboards as kb
from services import support as support_service
from utils import safe_edit

router = Router(name="support")


@router.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery) -> None:
    operators = await support_service.list_active()
    if not operators:
        await safe_edit(
            callback.message,
            "🆘 Служба поддержки временно недоступна. Попробуйте позже.",
            reply_markup=kb.back_home_kb(),
        )
    else:
        await safe_edit(
            callback.message,
            "🆘 Свяжитесь с нашей поддержкой:",
            reply_markup=kb.support_kb(operators),
        )
    await callback.answer()
