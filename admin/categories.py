"""Управление категориями каталога из админ-панели."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from filters import IsAdmin
from services import products as products_service
from states import AdminCategoryFSM
from utils import add_log, safe_edit

router = Router(name="admin_categories")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "a_categories")
async def cb_categories(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    categories = await products_service.list_categories(only_active=False)
    await safe_edit(callback.message, "📁 Категории товаров:", reply_markup=kb.admin_categories_kb(categories))
    await callback.answer()


@router.callback_query(F.data == "acat_add")
async def cb_category_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminCategoryFSM.entering_name)
    await callback.message.answer("Введите название новой категории:")
    await callback.answer()


@router.message(AdminCategoryFSM.entering_name, F.text)
async def process_new_category(message: Message, state: FSMContext) -> None:
    category = await products_service.create_category(message.text.strip())
    await add_log("category_created", message.from_user.id, {"category_id": category.id, "name": category.name})
    await state.clear()
    categories = await products_service.list_categories(only_active=False)
    await message.answer(f"✅ Категория «{category.name}» создана.", reply_markup=kb.admin_categories_kb(categories))


@router.callback_query(F.data.startswith("acat:"))
async def cb_category_detail(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[1])
    category = await products_service.get_category(category_id)
    if category is None:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    status = "включена ✅" if category.is_active else "скрыта 🚫"
    text = f"📁 {category.name}\n\nСтатус: {status}"
    await safe_edit(callback.message, text, reply_markup=kb.admin_category_detail_kb(category))
    await callback.answer()


@router.callback_query(F.data.startswith("acat_rename:"))
async def cb_category_rename(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[1])
    await state.set_state(AdminCategoryFSM.entering_new_name)
    await state.update_data(category_id=category_id)
    await callback.message.answer("Введите новое название категории:")
    await callback.answer()


@router.message(AdminCategoryFSM.entering_new_name, F.text)
async def process_rename_category(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await products_service.rename_category(data["category_id"], message.text.strip())
    await add_log("category_renamed", message.from_user.id, {"category_id": data["category_id"]})
    await state.clear()
    categories = await products_service.list_categories(only_active=False)
    await message.answer("✅ Название обновлено.", reply_markup=kb.admin_categories_kb(categories))


@router.callback_query(F.data.startswith("acat_toggle:"))
async def cb_category_toggle(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[1])
    await products_service.toggle_category(category_id)
    await add_log("category_toggled", callback.from_user.id, {"category_id": category_id})
    await cb_category_detail(callback)


@router.callback_query(F.data.startswith("acat_up:"))
async def cb_category_up(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[1])
    await products_service.move_category(category_id, -1)
    categories = await products_service.list_categories(only_active=False)
    await safe_edit(callback.message, "📁 Категории товаров:", reply_markup=kb.admin_categories_kb(categories))
    await callback.answer()


@router.callback_query(F.data.startswith("acat_down:"))
async def cb_category_down(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[1])
    await products_service.move_category(category_id, 1)
    categories = await products_service.list_categories(only_active=False)
    await safe_edit(callback.message, "📁 Категории товаров:", reply_markup=kb.admin_categories_kb(categories))
    await callback.answer()


@router.callback_query(F.data.startswith("acat_delete:"))
async def cb_category_delete(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[1])
    await products_service.delete_category(category_id)
    await add_log("category_deleted", callback.from_user.id, {"category_id": category_id})
    categories = await products_service.list_categories(only_active=False)
    await safe_edit(callback.message, "🗑 Категория удалена.\n\n📁 Категории товаров:", reply_markup=kb.admin_categories_kb(categories))
    await callback.answer()
