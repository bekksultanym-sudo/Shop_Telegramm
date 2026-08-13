"""Управление администраторами и их ролями (SUPER_ADMIN, ADMIN, SUPPORT)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from filters import IsAdmin, has_role
from models import AdminRole
from services import admins as admins_service
from states import AdminAdminsFSM
from utils import add_log, safe_edit

router = Router(name="admin_admins")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

DENY_TEXT = "❌ Эта функция доступна только SUPER_ADMIN."


@router.callback_query(F.data == "a_admins")
async def cb_admins(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    admins = await admins_service.list_admins()
    await safe_edit(callback.message, "👑 Администраторы:", reply_markup=kb.admin_admins_kb(admins))
    await callback.answer()


@router.callback_query(F.data == "aadmin_add")
async def cb_admin_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await has_role(callback.from_user.id, AdminRole.SUPER_ADMIN):
        await callback.answer(DENY_TEXT, show_alert=True)
        return
    await state.set_state(AdminAdminsFSM.entering_tg_id)
    await callback.message.answer("Введите Telegram ID нового администратора:")
    await callback.answer()


@router.message(AdminAdminsFSM.entering_tg_id, F.text)
async def process_admin_tg_id(message: Message, state: FSMContext) -> None:
    if not message.text.strip().lstrip("-").isdigit():
        await message.answer("Введите числовой Telegram ID.")
        return
    await state.update_data(tg_id=int(message.text.strip()))
    await state.set_state(AdminAdminsFSM.choosing_role)
    await message.answer("Выберите роль:", reply_markup=kb.admin_role_pick_kb())


@router.callback_query(AdminAdminsFSM.choosing_role, F.data.startswith("aadmin_role:"))
async def process_admin_role(callback: CallbackQuery, state: FSMContext) -> None:
    role = AdminRole(callback.data.split(":")[1])
    data = await state.get_data()
    admin = await admins_service.add_admin(data["tg_id"], username=None, role=role, added_by=callback.from_user.id)
    await add_log("admin_added", callback.from_user.id, {"tg_id": admin.tg_id, "role": role.value})
    await state.clear()
    admins = await admins_service.list_admins()
    await callback.message.answer(
        f"✅ Администратор {admin.tg_id} добавлен с ролью {role.value}.", reply_markup=kb.admin_admins_kb(admins)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("aadmin:"))
async def cb_admin_detail(callback: CallbackQuery) -> None:
    tg_id = int(callback.data.split(":")[1])
    admin = await admins_service.get_admin_by_tg_id(tg_id)
    if admin is None:
        await callback.answer("Администратор не найден", show_alert=True)
        return
    text = f"👑 Администратор\n\nID: <code>{admin.tg_id}</code>\nРоль: {admin.role.value}"
    await safe_edit(callback.message, text, reply_markup=kb.admin_admin_detail_kb(admin))
    await callback.answer()


@router.callback_query(F.data.startswith("aadmin_remove:"))
async def cb_admin_remove(callback: CallbackQuery) -> None:
    if not await has_role(callback.from_user.id, AdminRole.SUPER_ADMIN):
        await callback.answer(DENY_TEXT, show_alert=True)
        return
    tg_id = int(callback.data.split(":")[1])
    await admins_service.remove_admin(tg_id)
    await add_log("admin_removed", callback.from_user.id, {"tg_id": tg_id})
    admins = await admins_service.list_admins()
    await safe_edit(callback.message, "➖ Администратор удалён.\n\n👑 Администраторы:", reply_markup=kb.admin_admins_kb(admins))
    await callback.answer()
