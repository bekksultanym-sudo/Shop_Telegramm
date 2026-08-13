"""Модерация отзывов: публикация, скрытие, удаление, закрепление."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

import keyboards as kb
from filters import IsAdmin
from services import reviews as reviews_service
from utils import add_log, safe_edit

router = Router(name="admin_reviews")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "a_reviews")
async def cb_reviews(callback: CallbackQuery) -> None:
    reviews = await reviews_service.list_all()
    if not reviews:
        await safe_edit(callback.message, "Отзывов пока нет.", reply_markup=kb.admin_back_kb())
        await callback.answer()
        return
    await safe_edit(callback.message, "⭐ Отзывы:", reply_markup=kb.admin_reviews_kb(reviews))
    await callback.answer()


@router.callback_query(F.data.startswith("arev:"))
async def cb_review_detail(callback: CallbackQuery) -> None:
    review_id = int(callback.data.split(":")[1])
    review = await reviews_service.get_review(review_id)
    if review is None:
        await callback.answer("Отзыв не найден", show_alert=True)
        return
    stars = "⭐" * review.rating if review.rating else "—"
    status = "опубликован ✅" if review.is_published else "на проверке 🕓"
    pinned = " 📌 закреплён" if review.is_pinned else ""
    text = f"⭐ Отзыв №{review.id}{pinned}\n\nОценка: {stars}\nСтатус: {status}\n\n{review.text}"
    await safe_edit(callback.message, text, reply_markup=kb.admin_review_detail_kb(review))
    await callback.answer()


@router.callback_query(F.data.startswith("arev_publish:"))
async def cb_review_publish(callback: CallbackQuery) -> None:
    review_id = int(callback.data.split(":")[1])
    await reviews_service.set_published(review_id, True)
    await add_log("review_published", callback.from_user.id, {"review_id": review_id})
    await cb_review_detail(callback)


@router.callback_query(F.data.startswith("arev_hide:"))
async def cb_review_hide(callback: CallbackQuery) -> None:
    review_id = int(callback.data.split(":")[1])
    await reviews_service.set_published(review_id, False)
    await add_log("review_hidden", callback.from_user.id, {"review_id": review_id})
    await cb_review_detail(callback)


@router.callback_query(F.data.startswith("arev_pin:"))
async def cb_review_pin(callback: CallbackQuery) -> None:
    review_id = int(callback.data.split(":")[1])
    review = await reviews_service.get_review(review_id)
    await reviews_service.set_pinned(review_id, not review.is_pinned)
    await add_log("review_pin_toggled", callback.from_user.id, {"review_id": review_id})
    await cb_review_detail(callback)


@router.callback_query(F.data.startswith("arev_delete:"))
async def cb_review_delete(callback: CallbackQuery) -> None:
    review_id = int(callback.data.split(":")[1])
    await reviews_service.delete_review(review_id)
    await add_log("review_deleted", callback.from_user.id, {"review_id": review_id})
    reviews = await reviews_service.list_all()
    await safe_edit(callback.message, "🗑 Отзыв удалён.\n\n⭐ Отзывы:", reply_markup=kb.admin_reviews_kb(reviews))
    await callback.answer()
