"""Карточка товара: фото, описание, характеристики, переключение фотографий."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

import keyboards as kb
from services import products as products_service
from utils import format_price

router = Router(name="products")


def _build_caption(product) -> str:
    lines = [f"<b>{product.name}</b>", ""]
    if product.short_description:
        lines.append(product.short_description)
        lines.append("")
    if product.characteristics:
        lines.append(f"📋 <b>Характеристики:</b>\n{product.characteristics}")
        lines.append("")
    if product.full_description:
        lines.append(product.full_description)
        lines.append("")
    availability = f"✅ В наличии: {product.stock_quantity} шт." if product.stock_quantity > 0 else "⛔️ Нет в наличии"
    lines.append(availability)
    return "\n".join(lines)


async def _full_text(product) -> str:
    price_str = await format_price(product.price)
    return f"{_build_caption(product)}\n\n💰 Цена: {price_str}"


@router.callback_query(F.data.startswith("prod:"))
async def cb_product(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[1])
    product = await products_service.get_product(product_id)
    if product is None or not product.is_active:
        await callback.answer("Товар недоступен", show_alert=True)
        return

    text = await _full_text(product)
    markup = kb.product_card_kb(product, photo_index=0, photo_count=len(product.images))

    try:
        await callback.message.delete()
    except Exception:
        pass

    if product.images:
        await callback.message.answer_photo(photo=product.images[0].file_id, caption=text, reply_markup=markup)
    else:
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("prodphoto:"))
async def cb_product_photo(callback: CallbackQuery) -> None:
    _, product_id, index = callback.data.split(":")
    product_id, index = int(product_id), int(index)
    product = await products_service.get_product(product_id)
    if product is None or not product.images:
        await callback.answer()
        return
    index = index % len(product.images)
    text = await _full_text(product)
    markup = kb.product_card_kb(product, photo_index=index, photo_count=len(product.images))
    from aiogram.types import InputMediaPhoto

    await callback.message.edit_media(
        media=InputMediaPhoto(media=product.images[index].file_id, caption=text),
        reply_markup=markup,
    )
    await callback.answer()
