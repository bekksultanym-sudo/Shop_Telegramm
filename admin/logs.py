"""Просмотр логов действий (вход, заказы, чеки, бан, изменения и т.д.)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select, func

import keyboards as kb
from database import get_session
from filters import IsAdmin
from models import Log
from utils import safe_edit

router = Router(name="admin_logs")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PER_PAGE = 10


@router.callback_query(F.data == "a_logs")
async def cb_logs(callback: CallbackQuery) -> None:
    await _show_logs_page(callback, page=0)


@router.callback_query(F.data.startswith("alogs:"))
async def cb_logs_page(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":")[1])
    await _show_logs_page(callback, page)


async def _show_logs_page(callback: CallbackQuery, page: int) -> None:
    async with get_session() as session:
        total = (await session.execute(select(func.count(Log.id)))).scalar_one()
        total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
        page = max(0, min(page, total_pages - 1))
        stmt = select(Log).order_by(Log.created_at.desc()).offset(page * PER_PAGE).limit(PER_PAGE)
        result = await session.execute(stmt)
        logs = list(result.scalars().all())

    if not logs:
        await safe_edit(callback.message, "📜 Логи пусты.", reply_markup=kb.admin_back_kb())
        await callback.answer()
        return

    lines = []
    for log in logs:
        ts = log.created_at.strftime("%d.%m %H:%M")
        lines.append(f"<code>{ts}</code> {log.action} — id {log.tg_id}")
    text = f"📜 Логи (стр. {page+1}/{total_pages}):\n\n" + "\n".join(lines)
    await safe_edit(callback.message, text, reply_markup=kb.admin_logs_kb(page, total_pages))
    await callback.answer()
