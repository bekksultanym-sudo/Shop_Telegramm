"""Раздел «Мои заказы» — история заказов пользователя."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

import keyboards as kb
from models import OrderStatus
from services import orders as orders_service
from utils import format_price, get_or_create_user, safe_edit

router = Router(name="orders")

CANCELLABLE = {OrderStatus.NEW, OrderStatus.WAITING_PAYMENT, OrderStatus.PAYMENT_CHECK}


@router.callback_query(F.data == "my_orders")
async def cb_my_orders(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user)
    orders = await orders_service.list_user_orders(user.id)
    if not orders:
        await safe_edit(callback.message, "📦 У вас пока нет заказов.", reply_markup=kb.back_home_kb())
        await callback.answer()
        return
    await safe_edit(callback.message, "📦 Ваши заказы:", reply_markup=kb.my_orders_kb(orders))
    await callback.answer()


@router.callback_query(F.data.startswith("myorder:"))
async def cb_order_detail(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":")[1])
    order = await orders_service.get_order(order_id)
    if order is None:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    total_str = await format_price(order.total_amount)
    items_text = "\n".join(f"• {i.product_name} × {i.quantity}" for i in order.items)
    text = (
        f"📦 Заказ №{order.id}\n\n"
        f"{items_text}\n\n"
        f"💰 Сумма: {total_str}\n"
        f"📍 Адрес: {order.address or '—'}\n"
        f"📌 Статус: {order.status.value}"
    )
    can_cancel = order.status in CANCELLABLE
    await safe_edit(callback.message, text, reply_markup=kb.order_detail_kb(order.id, can_cancel))
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_order:"))
async def cb_cancel_order(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":")[1])
    order = await orders_service.get_order(order_id)
    if order is None or order.status not in CANCELLABLE:
        await callback.answer("Этот заказ уже нельзя отменить", show_alert=True)
        return
    await orders_service.cancel_order(order_id)
    await callback.answer("Заказ отменён")
    await cb_my_orders(callback)
