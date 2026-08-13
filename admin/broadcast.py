"""Рассылка сообщений всем пользователям с предпросмотром и защитой от лимитов."""
from __future__ import annotations

import asyncio
import json

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

import keyboards as kb
from config import config
from database import get_session
from filters import IsAdmin
from models import Broadcast, BroadcastStatus
from services import users as users_service
from states import AdminBroadcastFSM
from utils import add_log, safe_edit

router = Router(name="admin_broadcast")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "a_broadcast")
async def cb_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AdminBroadcastFSM.composing)
    await safe_edit(
        callback.message,
        "📢 Рассылка\n\nОтправьте текст, фото или видео (с подписью) для рассылки всем пользователям.",
        reply_markup=kb.admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminBroadcastFSM.composing, F.text | F.photo | F.video)
async def process_broadcast_content(message: Message, state: FSMContext) -> None:
    if message.photo:
        content_type, text, media_file_id = "photo", message.caption, message.photo[-1].file_id
    elif message.video:
        content_type, text, media_file_id = "video", message.caption, message.video.file_id
    else:
        content_type, text, media_file_id = "text", message.text, None

    await state.update_data(content_type=content_type, text=text, media_file_id=media_file_id)
    await state.set_state(AdminBroadcastFSM.confirming)

    preview_text = f"Предпросмотр рассылки:\n\n{text or ''}"
    if content_type == "photo":
        await message.answer_photo(media_file_id, caption=preview_text, reply_markup=kb.admin_broadcast_confirm_kb())
    elif content_type == "video":
        await message.answer_video(media_file_id, caption=preview_text, reply_markup=kb.admin_broadcast_confirm_kb())
    else:
        await message.answer(preview_text, reply_markup=kb.admin_broadcast_confirm_kb())
    await message.answer("Отправить рассылку?", reply_markup=kb.admin_broadcast_confirm_kb())


@router.callback_query(AdminBroadcastFSM.confirming, F.data == "abroadcast_cancel")
async def cb_broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("❌ Рассылка отменена.", reply_markup=kb.admin_back_kb())
    await callback.answer()


@router.callback_query(AdminBroadcastFSM.confirming, F.data == "abroadcast_send")
async def cb_broadcast_send(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    await state.clear()

    recipient_ids = await users_service.list_all_tg_ids(exclude_banned=True)

    async with get_session() as session:
        broadcast = Broadcast(
            admin_id=callback.from_user.id,
            content_type=data["content_type"],
            text=data.get("text"),
            media_file_id=data.get("media_file_id"),
            status=BroadcastStatus.SENDING,
            total_recipients=len(recipient_ids),
        )
        session.add(broadcast)
        await session.commit()
        await session.refresh(broadcast)

    await callback.answer("Рассылка запущена")
    await callback.message.answer(f"📢 Рассылка запущена для {len(recipient_ids)} пользователей...")

    sent, failed = 0, 0
    delay = 1 / max(config.broadcast_rate_per_sec, 1)

    for tg_id in recipient_ids:
        try:
            if data["content_type"] == "photo":
                await bot.send_photo(tg_id, data["media_file_id"], caption=data.get("text"))
            elif data["content_type"] == "video":
                await bot.send_video(tg_id, data["media_file_id"], caption=data.get("text"))
            else:
                await bot.send_message(tg_id, data.get("text") or "")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(delay)

    async with get_session() as session:
        b = await session.get(Broadcast, broadcast.id)
        if b:
            b.sent_count = sent
            b.failed_count = failed
            b.status = BroadcastStatus.DONE
            await session.commit()

    await add_log("broadcast_sent", callback.from_user.id, {"broadcast_id": broadcast.id, "sent": sent, "failed": failed})
    await callback.message.answer(f"✅ Рассылка завершена.\nДоставлено: {sent}\nОшибок: {failed}")
