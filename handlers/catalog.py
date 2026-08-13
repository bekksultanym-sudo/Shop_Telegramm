"""Раздел «Каталог»: категории и список товаров."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

import keyboards as kb
from services import products as products_service
from utils import paginate, safe_edit

router = Router(name="catalog")

PER_PAGE = 8


@router.callback_query(F.data == "catalog")
async def cb_catalog(callback: CallbackQuery) -> None:
    categories = await products_service.list_categories()
    if not categories:
        await safe_edit(callback.message, "Каталог пока пуст. Загляните позже 🙌", reply_markup=kb.back_home_kb())
        await callback.answer()
        return
    await safe_edit(callback.message, "🛍 Выберите категорию:", reply_markup=kb.categories_kb(categories))
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def cb_category(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[1])
    await _show_category_page(callback, category_id, page=0)


@router.callback_query(F.data.startswith("catpage:"))
async def cb_category_page(callback: CallbackQuery) -> None:
    _, category_id, page = callback.data.split(":")
    await _show_category_page(callback, int(category_id), int(page))


async def _show_category_page(callback: CallbackQuery, category_id: int, page: int) -> None:
    category = await products_service.get_category(category_id)
    if category is None:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    products = await products_service.list_products(category_id)
    if not products:
        await safe_edit(
            callback.message,
            f"📁 {category.name}\n\nВ этой категории пока нет товаров.",
            reply_markup=kb.back_home_kb(back_cb="catalog"),
        )
        await callback.answer()
        return
    page_items, total_pages = paginate(products, page, PER_PAGE)
    await safe_edit(
        callback.message,
        f"📁 {category.name}\n\nВыберите товар:",
        reply_markup=kb.products_kb(page_items, category_id, page, total_pages),
    )
    await callback.answer()
