"""Управление способами оплаты (реквизиты) из админ-панели."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from filters import IsAdmin
from services import payments as payments_service
from states import AdminPaymentMethodFSM
from utils import add_log, safe_edit

router = Router(name="admin_payments")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "a_payments")
async def cb_payments(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    methods = await payments_service.list_methods(only_active=False)
    await safe_edit(callback.message, "💳 Способы оплаты:", reply_markup=kb.admin_payments_kb(methods))
    await callback.answer()


@router.callback_query(F.data == "apay_add")
async def cb_payment_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminPaymentMethodFSM.entering_name)
    await callback.message.answer("Введите название способа оплаты (например «Kaspi Gold»):")
    await callback.answer()


@router.message(AdminPaymentMethodFSM.entering_name, F.text)
async def process_payment_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminPaymentMethodFSM.entering_details)
    await message.answer("Введите реквизиты (номер карты/счёта и т.п.):")


@router.message(AdminPaymentMethodFSM.entering_details, F.text)
async def process_payment_details(message: Message, state: FSMContext) -> None:
    await state.update_data(details=message.text.strip())
    await state.set_state(AdminPaymentMethodFSM.entering_instructions)
    await message.answer("Введите инструкцию для покупателя (или «-», чтобы пропустить):")


@router.message(AdminPaymentMethodFSM.entering_instructions, F.text)
async def process_payment_instructions(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    instructions = None if message.text.strip() == "-" else message.text.strip()
    method = await payments_service.create_method(data["name"], data["details"], instructions)
    await add_log("payment_method_created", message.from_user.id, {"method_id": method.id, "name": method.name})
    await state.clear()
    methods = await payments_service.list_methods(only_active=False)
    await message.answer(f"✅ Способ оплаты «{method.name}» добавлен.", reply_markup=kb.admin_payments_kb(methods))


@router.callback_query(F.data.startswith("apay:"))
async def cb_payment_detail(callback: CallbackQuery) -> None:
    method_id = int(callback.data.split(":")[1])
    method = await payments_service.get_method(method_id)
    if method is None:
        await callback.answer("Способ оплаты не найден", show_alert=True)
        return
    status = "включён ✅" if method.is_active else "скрыт 🚫"
    text = f"💳 <b>{method.name}</b>\n\nРеквизиты: {method.details}\n"
    if method.instructions:
        text += f"Инструкция: {method.instructions}\n"
    text += f"\nСтатус: {status}"
    await safe_edit(callback.message, text, reply_markup=kb.admin_payment_detail_kb(method))
    await callback.answer()


@router.callback_query(F.data.startswith("apay_toggle:"))
async def cb_payment_toggle(callback: CallbackQuery) -> None:
    method_id = int(callback.data.split(":")[1])
    await payments_service.toggle_method(method_id)
    await add_log("payment_method_toggled", callback.from_user.id, {"method_id": method_id})
    await cb_payment_detail(callback)


@router.callback_query(F.data.startswith("apay_delete:"))
async def cb_payment_delete(callback: CallbackQuery) -> None:
    method_id = int(callback.data.split(":")[1])
    await payments_service.delete_method(method_id)
    await add_log("payment_method_deleted", callback.from_user.id, {"method_id": method_id})
    methods = await payments_service.list_methods(only_active=False)
    await safe_edit(callback.message, "🗑 Способ оплаты удалён.\n\n💳 Способы оплаты:", reply_markup=kb.admin_payments_kb(methods))
    await callback.answer()
