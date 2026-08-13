"""Оформление заказа: вариант → количество → адрес → сумма заказа."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from services import orders as orders_service
from services import products as products_service
from states import OrderFSM
from utils import add_log, format_price, get_or_create_user, safe_edit

router = Router(name="cart")


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = int(callback.data.split(":")[1])
    product = await products_service.get_product(product_id)
    if product is None or product.stock_quantity <= 0:
        await callback.answer("Товар недоступен", show_alert=True)
        return

    if product.variants:
        await state.set_state(OrderFSM.choosing_variant)
        await state.update_data(product_id=product_id)
        await callback.message.answer(
            f"Выберите вариант товара «{product.name}»:",
            reply_markup=kb.variants_kb(product_id, product.variants),
        )
    else:
        await _start_quantity(callback.message, state, product_id, variant_id=None)
    await callback.answer()


@router.callback_query(OrderFSM.choosing_variant, F.data.startswith("variant:"))
async def cb_variant(callback: CallbackQuery, state: FSMContext) -> None:
    _, product_id, variant_id = callback.data.split(":")
    await _start_quantity(callback.message, state, int(product_id), int(variant_id))
    await callback.answer()


async def _start_quantity(message: Message, state: FSMContext, product_id: int, variant_id: int | None) -> None:
    product = await products_service.get_product(product_id)
    max_qty = product.stock_quantity
    if variant_id:
        variant = next((v for v in product.variants if v.id == variant_id), None)
        if variant:
            max_qty = min(max_qty, variant.stock_quantity) if variant.stock_quantity else max_qty
    await state.set_state(OrderFSM.choosing_quantity)
    await state.update_data(product_id=product_id, variant_id=variant_id, max_qty=max_qty)
    await message.answer(
        f"Сколько штук «{product.name}» вы хотите заказать?",
        reply_markup=kb.quantity_kb(product_id, qty=1, max_qty=max(1, max_qty)),
    )


@router.callback_query(OrderFSM.choosing_quantity, F.data.startswith("qty:"))
async def cb_quantity_change(callback: CallbackQuery, state: FSMContext) -> None:
    _, product_id, qty = callback.data.split(":")
    data = await state.get_data()
    max_qty = max(1, data.get("max_qty", 99))
    await safe_edit(
        callback.message,
        callback.message.text or callback.message.caption or "Выберите количество:",
        reply_markup=kb.quantity_kb(int(product_id), qty=int(qty), max_qty=max_qty),
    )
    await callback.answer()


@router.callback_query(OrderFSM.choosing_quantity, F.data.startswith("qtyconfirm:"))
async def cb_quantity_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    _, product_id, qty = callback.data.split(":")
    await state.update_data(quantity=int(qty))
    await state.set_state(OrderFSM.entering_address)
    await safe_edit(
        callback.message,
        "📍 Укажите адрес доставки одним сообщением:",
        reply_markup=kb.back_home_kb(),
    )
    await callback.answer()


@router.message(OrderFSM.entering_address, F.text)
async def process_address(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    product = await products_service.get_product(data["product_id"])
    variant = None
    if data.get("variant_id"):
        variant = next((v for v in product.variants if v.id == data["variant_id"]), None)

    user = await get_or_create_user(message.from_user)
    order = await orders_service.create_order(user.id, product, variant, data["quantity"])
    await orders_service.set_address(order.id, message.text.strip())
    await add_log("order_created", message.from_user.id, {"order_id": order.id})

    await state.set_state(OrderFSM.choosing_payment)
    await state.update_data(order_id=order.id)

    total_str = await format_price(order.total_amount)
    item_name = product.name if not variant else f"{product.name} ({variant.name})"
    text = (
        f"📦 Заказ №{order.id}\n\n"
        f"Товар: {item_name}\n"
        f"Количество: {data['quantity']}\n"
        f"Доставка: {message.text.strip()}\n"
        f"Итого: {total_str}"
    )
    await message.answer(text, reply_markup=kb.order_summary_kb())


@router.callback_query(F.data == "order_cancel")
async def cb_order_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("order_id"):
        await orders_service.cancel_order(data["order_id"])
    await state.clear()
    await safe_edit(callback.message, "❌ Оформление заказа отменено.", reply_markup=kb.back_home_kb())
    await callback.answer()
