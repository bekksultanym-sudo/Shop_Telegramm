"""Общие вспомогательные функции."""
from __future__ import annotations

import json
from decimal import Decimal

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message, User as TgUser
from sqlalchemy import select

from database import get_session
from models import Log, User
from services import settings as settings_service


async def get_or_create_user(tg_user: TgUser) -> User:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                tg_id=tg_user.id,
                username=tg_user.username,
                full_name=tg_user.full_name,
            )
            session.add(user)
        else:
            user.username = tg_user.username
            user.full_name = tg_user.full_name
        await session.commit()
        await session.refresh(user)
        return user


async def add_log(action: str, tg_id: int | None, details: dict | None = None) -> None:
    async with get_session() as session:
        session.add(
            Log(
                action=action,
                tg_id=tg_id,
                details=json.dumps(details, ensure_ascii=False) if details else None,
            )
        )
        await session.commit()


async def format_price(amount: Decimal | float) -> str:
    currency = await settings_service.get("currency")
    return f"{Decimal(amount):,.0f}".replace(",", " ") + f" {currency}"


async def safe_edit(message: Message, text: str, reply_markup=None, **kwargs) -> None:
    """Редактирует сообщение, тихо игнорируя ошибку 'message is not modified'."""
    try:
        await message.edit_text(text, reply_markup=reply_markup, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


async def answer_callback_safely(callback: CallbackQuery, text: str | None = None, show_alert: bool = False) -> None:
    try:
        await callback.answer(text, show_alert=show_alert)
    except TelegramBadRequest:
        pass


def paginate(items: list, page: int, per_page: int = 8) -> tuple[list, int]:
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    return items[start : start + per_page], total_pages
