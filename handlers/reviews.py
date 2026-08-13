"""Раздел «Отзывы»: просмотр и добавление после завершённого заказа."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import keyboards as kb
from services import reviews as reviews_service
from states import ReviewFSM
from utils import get_or_create_user, safe_edit

router = Router(name="reviews")


@router.callback_query(F.data == "reviews")
async def cb_reviews(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user)
    reviews = await reviews_service.list_published()
    eligible_order_id = await reviews_service.has_completed_order_without_review(user.id)

    if reviews:
        chunks = []
        for r in reviews[:10]:
            pin = "📌 " if r.is_pinned else ""
            stars = "⭐" * r.rating if r.rating else ""
            chunks.append(f"{pin}{stars}\n{r.text}")
        text = "⭐ Отзывы покупателей:\n\n" + "\n\n➖➖➖\n\n".join(chunks)
    else:
        text = "⭐ Пока нет отзывов. Будьте первым!"

    kb_builder = InlineKeyboardBuilder()
    if eligible_order_id:
        kb_builder.button(text="✍️ Оставить отзыв", callback_data=f"review_write:{eligible_order_id}")
    kb_builder.row(*kb.nav_row(home=True))

    await safe_edit(callback.message, text, reply_markup=kb_builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("review_write:"))
async def cb_review_write(callback: CallbackQuery, state: FSMContext) -> None:
    order_id = int(callback.data.split(":")[1])
    await state.set_state(ReviewFSM.entering_text)
    await state.update_data(order_id=order_id)
    await callback.message.answer("✍️ Напишите текст отзыва одним сообщением:")
    await callback.answer()


@router.message(ReviewFSM.entering_text, F.text)
async def process_review_text(message: Message, state: FSMContext) -> None:
    await state.update_data(text=message.text.strip())
    await state.set_state(ReviewFSM.entering_rating)
    kb_builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb_builder.button(text="⭐" * i, callback_data=f"review_rating:{i}")
    kb_builder.adjust(5)
    await message.answer("Оцените заказ от 1 до 5 звёзд:", reply_markup=kb_builder.as_markup())


@router.callback_query(ReviewFSM.entering_rating, F.data.startswith("review_rating:"))
async def process_review_rating(callback: CallbackQuery, state: FSMContext) -> None:
    rating = int(callback.data.split(":")[1])
    data = await state.get_data()
    user = await get_or_create_user(callback.from_user)
    await reviews_service.create_review(user.id, data.get("order_id"), data["text"], rating)
    await state.clear()
    await safe_edit(
        callback.message,
        "🙏 Спасибо за отзыв! Он появится в разделе «Отзывы» после проверки администратором.",
        reply_markup=kb.back_home_kb(),
    )
    await callback.answer()
