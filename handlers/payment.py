"""Выбор способа оплаты и отправка чека."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from models import ReceiptType
from services import admins as admins_service
from services import orders as orders_service
from services import payments as payments_service
from states import OrderFSM
from utils import add_log, format_price, safe_edit

router = Router(name="payment")


@router.callback_query(OrderFSM.choosing_payment, F.data == "order_pay")
async def cb_order_pay(callback: CallbackQuery) -> None:
    methods = await payments_service.list_methods()
    if not methods:
        await callback.answer("Способы оплаты пока не настроены. Обратитесь в поддержку.", show_alert=True)
        return
    await safe_edit(callback.message, "💳 Выберите способ оплаты:", reply_markup=kb.payment_methods_kb(methods))
    await callback.answer()


@router.callback_query(OrderFSM.choosing_payment, F.data.startswith("paymethod:"))
async def cb_payment_method(callback: CallbackQuery, state: FSMContext) -> None:
    method_id = int(callback.data.split(":")[1])
    method = await payments_service.get_method(method_id)
    if method is None:
        await callback.answer("Способ оплаты недоступен", show_alert=True)
        return

    data = await state.get_data()
    await orders_service.set_payment_method(data["order_id"], method_id)
    await state.set_state(OrderFSM.uploading_receipt)

    text = f"💳 <b>{method.name}</b>\n\n{method.details}"
    if method.instructions:
        text += f"\n\n📝 {method.instructions}"
    text += "\n\nПосле оплаты нажмите кнопку ниже и отправьте фото или файл чека."
    await safe_edit(callback.message, text, reply_markup=kb.after_payment_details_kb())
    await callback.answer()


@router.callback_query(OrderFSM.uploading_receipt, F.data == "send_receipt")
async def cb_send_receipt(callback: CallbackQuery) -> None:
    await callback.message.answer("📎 Отправьте фотографию или файл чека следующим сообщением.")
    await callback.answer()


@router.message(OrderFSM.uploading_receipt, F.photo | F.document)
async def process_receipt(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    order_id = data.get("order_id")
    if not order_id:
        await message.answer("Не удалось найти заказ. Попробуйте оформить заново из главного меню.")
        await state.clear()
        return

    if message.photo:
        file_id = message.photo[-1].file_id
        receipt_type = ReceiptType.PHOTO
    else:
        file_id = message.document.file_id
        receipt_type = ReceiptType.DOCUMENT

    await orders_service.attach_receipt(order_id, file_id, receipt_type)
    await add_log("receipt_sent", message.from_user.id, {"order_id": order_id})

    order = await orders_service.get_order(order_id)
    await message.answer(
        f"✅ Чек по заказу №{order_id} получен.\n⏳ Ожидает подтверждения администратором.",
    )
    await state.clear()

    await _notify_admins(bot, order)


async def _notify_admins(bot: Bot, order) -> None:
    admin_ids = await admins_service.list_admin_tg_ids()
    total_str = await format_price(order.total_amount)
    items_text = "\n".join(f"• {i.product_name} × {i.quantity}" for i in order.items)
    caption = (
        f"📦 Заказ №{order.id}\n"
        f"👤 Пользователь: {order.user.full_name or order.user.tg_id} (id {order.user.tg_id})\n"
        f"🛍 Товары:\n{items_text}\n"
        f"💰 Сумма: {total_str}\n"
        f"📍 Адрес: {order.address}\n"
        f"💳 Способ оплаты: {order.payment_method.name if order.payment_method else '—'}\n"
        f"🧾 Чек прикреплён"
    )
    markup = kb.admin_order_review_kb(order.id)
    for admin_id in admin_ids:
        try:
            if order.payment and order.payment.receipt_type == ReceiptType.PHOTO:
                await bot.send_photo(admin_id, order.payment.receipt_file_id, caption=caption, reply_markup=markup)
            else:
                await bot.send_document(admin_id, order.payment.receipt_file_id, caption=caption, reply_markup=markup)
        except Exception:
            continue
