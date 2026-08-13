"""Управление контактами техподдержки из админ-панели."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from filters import IsAdmin
from services import support as support_service
from states import AdminSupportFSM
from utils import add_log, safe_edit

router = Router(name="admin_support")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "a_support")
async def cb_support(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    operators = await support_service.list_all()
    await safe_edit(callback.message, "🆘 Операторы техподдержки:", reply_markup=kb.admin_support_kb(operators))
    await callback.answer()


@router.callback_query(F.data == "asup_add")
async def cb_support_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminSupportFSM.entering_username)
    await callback.message.answer("Введите username оператора (например @support_admin или support_admin):")
    await callback.answer()


@router.message(AdminSupportFSM.entering_username, F.text)
async def process_support_username(message: Message, state: FSMContext) -> None:
    await state.update_data(username=message.text.strip())
    await state.set_state(AdminSupportFSM.entering_label)
    await message.answer("Введите отображаемое имя оператора (или «-», чтобы использовать username):")


@router.message(AdminSupportFSM.entering_label, F.text)
async def process_support_label(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    label = None if message.text.strip() == "-" else message.text.strip()
    contact = await support_service.add_contact(data["username"], label)
    await add_log("support_contact_added", message.from_user.id, {"contact_id": contact.id})
    await state.clear()
    operators = await support_service.list_all()
    await message.answer(f"✅ Оператор @{contact.username} добавлен.", reply_markup=kb.admin_support_kb(operators))


@router.callback_query(F.data.startswith("asup:"))
async def cb_support_detail(callback: CallbackQuery) -> None:
    contact_id = int(callback.data.split(":")[1])
    contact = await support_service.get_contact(contact_id)
    if contact is None:
        await callback.answer("Оператор не найден", show_alert=True)
        return
    status = "включён ✅" if contact.is_active else "скрыт 🚫"
    text = f"🆘 @{contact.username}\n{contact.label or ''}\n\nСтатус: {status}"
    await safe_edit(callback.message, text, reply_markup=kb.admin_support_detail_kb(contact))
    await callback.answer()


@router.callback_query(F.data.startswith("asup_toggle:"))
async def cb_support_toggle(callback: CallbackQuery) -> None:
    contact_id = int(callback.data.split(":")[1])
    await support_service.toggle_contact(contact_id)
    await add_log("support_contact_toggled", callback.from_user.id, {"contact_id": contact_id})
    await cb_support_detail(callback)


@router.callback_query(F.data.startswith("asup_delete:"))
async def cb_support_delete(callback: CallbackQuery) -> None:
    contact_id = int(callback.data.split(":")[1])
    await support_service.delete_contact(contact_id)
    await add_log("support_contact_deleted", callback.from_user.id, {"contact_id": contact_id})
    operators = await support_service.list_all()
    await safe_edit(callback.message, "🗑 Оператор удалён.\n\n🆘 Операторы техподдержки:", reply_markup=kb.admin_support_kb(operators))
    await callback.answer()
