"""Управление заказами: фильтры по статусу, подтверждение/отклонение оплаты."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from filters import IsAdmin
from models import OrderStatus
from services import orders as orders_service
from states import AdminOrderFSM
from utils import add_log, format_price, safe_edit

router = Router(name="admin_orders")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PER_PAGE = 8


@router.callback_query(F.data == "a_orders")
async def cb_orders(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback.message, "📦 Заказы. Выберите фильтр:", reply_markup=kb.admin_orders_filter_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("aordersf:"))
async def cb_orders_filtered(callback: CallbackQuery) -> None:
    _, status_value, page = callback.data.split(":")
    status = OrderStatus(status_value)
    orders = await orders_service.list_orders_by_status(status)
    if not orders:
        await safe_edit(
            callback.message, f"Заказов со статусом «{status.value}» нет.", reply_markup=kb.admin_orders_filter_kb()
        )
        await callback.answer()
        return
    page = int(page)
    from utils import paginate

    page_items, total_pages = paginate(orders, page, PER_PAGE)
    await safe_edit(
        callback.message,
        f"📦 Заказы: {status.value}",
        reply_markup=kb.admin_orders_list_kb(page_items, status.value, page, total_pages),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("aorder:"))
async def cb_order_detail(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":")[1])
    order = await orders_service.get_order(order_id)
    if order is None:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    text = await _order_text(order)
    await safe_edit(callback.message, text, reply_markup=kb.admin_order_status_kb(order))
    await callback.answer()


async def _order_text(order) -> str:
    total_str = await format_price(order.total_amount)
    items_text = "\n".join(f"• {i.product_name} × {i.quantity}" for i in order.items)
    return (
        f"📦 Заказ №{order.id}\n\n"
        f"👤 Пользователь: {order.user.full_name or order.user.tg_id} (id {order.user.tg_id})\n"
        f"🛍 {items_text}\n"
        f"💰 Сумма: {total_str}\n"
        f"📍 Адрес: {order.address or '—'}\n"
        f"💳 Способ оплаты: {order.payment_method.name if order.payment_method else '—'}\n"
        f"📌 Статус: {order.status.value}"
    )


@router.callback_query(F.data.startswith("aorder_status:"))
async def cb_order_set_status(callback: CallbackQuery) -> None:
    _, order_id, status_value = callback.data.split(":")
    await orders_service.set_status(int(order_id), OrderStatus(status_value))
    await add_log("order_status_changed", callback.from_user.id, {"order_id": order_id, "status": status_value})
    order = await orders_service.get_order(int(order_id))
    text = await _order_text(order)
    await safe_edit(callback.message, text, reply_markup=kb.admin_order_status_kb(order))
    await callback.answer("Статус обновлён")


@router.callback_query(F.data.startswith("aorder_confirm:"))
async def cb_order_confirm_payment(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":")[1])
    await orders_service.confirm_payment(order_id, callback.from_user.id)
    await add_log("payment_confirmed", callback.from_user.id, {"order_id": order_id})
    await callback.answer("✅ Оплата подтверждена")
    try:
        await callback.message.edit_caption(caption=(callback.message.caption or "") + "\n\n✅ Оплата подтверждена")
    except Exception:
        pass
    await _notify_user_status(callback, order_id, "✅ Ваша оплата подтверждена! Заказ передан в обработку.")


@router.callback_query(F.data.startswith("aorder_reject:"))
async def cb_order_reject_payment(callback: CallbackQuery, state: FSMContext) -> None:
    order_id = int(callback.data.split(":")[1])
    await state.set_state(AdminOrderFSM.entering_reject_reason)
    await state.update_data(order_id=order_id)
    await callback.message.answer("Укажите причину отклонения оплаты (или отправьте «-»):")
    await callback.answer()


@router.message(AdminOrderFSM.entering_reject_reason, F.text)
async def process_reject_reason(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    order_id = data["order_id"]
    await orders_service.reject_payment(order_id, message.from_user.id)
    await add_log("payment_rejected", message.from_user.id, {"order_id": order_id, "reason": message.text})
    await state.clear()
    await message.answer(f"❌ Оплата по заказу №{order_id} отклонена.")

    reason = "" if message.text.strip() == "-" else f"\nПричина: {message.text.strip()}"
    await _notify_user_raw(message, order_id, f"❌ Оплата по заказу №{order_id} отклонена.{reason}\nСвяжитесь с поддержкой.")


async def _notify_user_status(callback: CallbackQuery, order_id: int, text: str) -> None:
    order = await orders_service.get_order(order_id)
    if order is None:
        return
    try:
        await callback.bot.send_message(order.user.tg_id, text)
    except Exception:
        pass


async def _notify_user_raw(message: Message, order_id: int, text: str) -> None:
    order = await orders_service.get_order(order_id)
    if order is None:
        return
    try:
        await message.bot.send_message(order.user.tg_id, text)
    except Exception:
        pass
