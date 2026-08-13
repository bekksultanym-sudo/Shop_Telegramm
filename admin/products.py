"""Управление товарами: список, добавление через пошаговый диалог, редактирование."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import keyboards as kb
from filters import IsAdmin
from services import products as products_service
from states import AdminProductEditFSM, AdminProductFSM
from utils import add_log, format_price, safe_edit

router = Router(name="admin_products")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

SKIP = "-"


# --------------------------- Список / категория ----------------------------

@router.callback_query(F.data == "a_products")
async def cb_products(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    categories = await products_service.list_categories(only_active=False)
    if not categories:
        await safe_edit(
            callback.message,
            "Сначала создайте категорию в разделе «📁 Категории».",
            reply_markup=kb.admin_back_kb(),
        )
        await callback.answer()
        return
    await safe_edit(
        callback.message,
        "🛍 Выберите категорию для управления товарами:",
        reply_markup=kb.admin_categories_pick_kb(categories, prefix="a_products_cat"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("a_products_cat:"))
async def cb_products_by_category(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[1])
    products = await products_service.list_products(category_id, only_active=False)
    category = await products_service.get_category(category_id)
    text = f"🛍 Товары в категории «{category.name}»:" if products else f"В категории «{category.name}» пока нет товаров."
    await safe_edit(callback.message, text, reply_markup=kb.admin_products_list_kb(products, category_id))
    await callback.answer()


@router.callback_query(F.data.startswith("aprod:"))
async def cb_product_detail(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[1])
    product = await products_service.get_product(product_id)
    if product is None:
        await callback.answer("Товар не найден", show_alert=True)
        return
    price_str = await format_price(product.price)
    status = "в продаже ✅" if product.is_active else "скрыт 🚫"
    text = (
        f"🛍 <b>{product.name}</b>\n\n"
        f"Цена: {price_str}\n"
        f"Количество: {product.stock_quantity}\n"
        f"Статус: {status}\n"
        f"Фото: {len(product.images)}\n"
        f"Вариантов: {len(product.variants)}"
    )
    await safe_edit(callback.message, text, reply_markup=kb.admin_product_detail_kb(product))
    await callback.answer()


@router.callback_query(F.data.startswith("aprod_toggle:"))
async def cb_product_toggle(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[1])
    await products_service.toggle_product(product_id)
    await add_log("product_toggled", callback.from_user.id, {"product_id": product_id})
    await cb_product_detail(callback)


@router.callback_query(F.data.startswith("aprod_delete:"))
async def cb_product_delete(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[1])
    product = await products_service.get_product(product_id)
    category_id = product.category_id if product else None
    await products_service.delete_product(product_id)
    await add_log("product_deleted", callback.from_user.id, {"product_id": product_id})
    if category_id:
        products = await products_service.list_products(category_id, only_active=False)
        await safe_edit(
            callback.message, "🗑 Товар удалён.", reply_markup=kb.admin_products_list_kb(products, category_id)
        )
    await callback.ans)


# ------------------------------ Мастер добавления ---------------------------

@router.callback_query(F.data.startswith("aprod_add:"))
async def cb_product_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[1])
    await state.set_state(AdminProductFSM.entering_name)
    await state.update_data(category_id=category_id, images=[], variants=[])
    await callback.message.answer("➕ Добавление товара.\n\n1️⃣ Введите название товара:")
    await callback.answer()


@router.message(AdminProductFSM.entering_name, F.text)
async def add_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminProductFSM.uploading_photo)
    await message.answer("2️⃣ Отправьте фотографию товара:")


@router.message(AdminProductFSM.uploading_photo, F.photo)
async def add_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    images = data.get("images", [])
    images.append(message.photo[-1].file_id)
    await state.update_data(images=images)
    await state.set_state(AdminProductFSM.uploading_more_photos)
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="✅ Готово, продолжить", callback_data="aprod_photos_done")
    await message.answer(
        "3️⃣ Можете отправить ещё фотографии, либо нажмите «Готово».",
        reply_markup=kb_builder.as_markup(),
    )


@router.message(AdminProductFSM.uploading_more_photos, F.photo)
async def add_more_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    images = data.get("images", [])
    images.append(message.photo[-1].file_id)
    await state.update_data(images=images)
    await message.answer(f"Фото добавлено ({len(images)}). Ещё, или «Готово».")


@router.callback_query(AdminProductFSM.uploading_more_photos, F.data == "aprod_photos_done")
async def photos_done(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminProductFSM.entering_price)
    await callback.message.answer("4️⃣ Введите цену товара (число, например 4990):")
    await callback.answer()


@router.message(AdminProductFSM.entering_price, F.text)
async def add_price(message: Message, state: FSMContext) -> None:
    try:
        price = Decimal(message.text.strip().replace(",", "."))
    except InvalidOperation:
        await message.answer("Введите цену числом, например: 4990")
        return
    await state.update_data(price=str(price))
    await state.set_state(AdminProductFSM.entering_short_description)
    await message.answer(f"5️⃣ Краткое описание товара (или «{SKIP}», чтобы пропустить):")


@router.message(AdminProductFSM.entering_short_description, F.text)
async def add_short_desc(message: Message, state: FSMContext) -> None:
    value = None if message.text.strip() == SKIP else message.text.strip()
    await state.update_data(short_description=value)
    await state.set_state(AdminProductFSM.entering_full_description)
    await message.answer(f"6️⃣ Полное описание товара (или «{SKIP}»):")


@router.message(AdminProductFSM.entering_full_description, F.text)
async def add_full_desc(message: Message, state: FSMContext) -> None:
    value = None if message.text.strip() == SKIP else message.text.strip()
    await state.update_data(full_description=value)
    await state.set_state(AdminProductFSM.entering_characteristics)
    await message.answer(f"7️⃣ Характеристики товара (или «{SKIP}»):")


@router.message(AdminProductFSM.entering_characteristics, F.text)
async def add_characteristics(message: Message, state: FSMContext) -> None:
    value = None if message.text.strip() == SKIP else message.text.strip()
    await state.update_data(characteristics=value)
    await state.set_state(AdminProductFSM.entering_quantity)
    await message.answer("8️⃣ Количество на складе (целое число):")


@router.message(AdminProductFSM.entering_quantity, F.text)
async def add_quantity(message: Message, state: FSMContext) -> None:
    if not message.text.strip().isdigit():
        await message.answer("Введите целое число, например: 25")
        return
    await state.update_data(stock_quantity=int(message.text.strip()))
    await state.set_state(AdminProductFSM.entering_variants)
    await message.answer(
        "9️⃣ Варианты товара (например «Красный:0:5», «Синий:+500:3» — по одному в строке).\n"
        f"Если вариантов нет, отправьте «{SKIP}»."
    )


@router.message(AdminProductFSM.entering_variants, F.text)
async def add_variants(message: Message, state: FSMContext) -> None:
    variants: list[dict] = []
    if message.text.strip() != SKIP:
        for line in message.text.strip().splitlines():
            parts = [p.strip() for p in line.split(":")]
            if not parts or not parts[0]:
                continue
            name = parts[0]
            try:
                modifier = Decimal(parts[1].replace("+", "")) if len(parts) > 1 and parts[1] else Decimal("0")
            except InvalidOperation:
                modifier = Decimal("0")
            qty = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
            variants.append({"name": name, "price_modifier": str(modifier), "stock_quantity": qty})
    await state.update_data(variants=variants)
    await state.set_state(AdminProductFSM.confirming)

    data = await state.get_data()
    price_str = await format_price(Decimal(data["price"]))
    summary = (
        f"🔟 Проверьте товар:\n\n"
        f"Название: {data['name']}\n"
        f"Цена: {price_str}\n"
        f"Количество: {data['stock_quantity']}\n"
        f"Фото: {len(data.get('images', []))}\n"
        f"Вариантов: {len(variants)}\n\n"
        f"Всё верно?"
    )
    kb_confirm = kb.confirm_kb("aprod_confirm", "aprod_discard", yes_text="✅ Сохранить", no_text="❌ Отменить")
    await message.answer(summary, reply_markup=kb_confirm)


@router.callback_query(AdminProductFSM.confirming, F.data == "aprod_confirm")
async def confirm_product(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    product = await products_service.create_product(
        category_id=data["category_id"],
        name=data["name"],
        short_description=data.get("short_description"),
        full_description=data.get("full_description"),
        characteristics=data.get("characteristics"),
        price=Decimal(data["price"]),
        stock_quantity=data["stock_quantity"],
    )
    for i, file_id in enumerate(data.get("images", [])):
        await products_service.add_product_image(product.id, file_id, sort_order=i)
    for v in data.get("variants", []):
        await products_service.add_product_variant(
            product.id, v["name"], Decimal(v["price_modifier"]), v["stock_quantity"]
        )
    await add_log("product_created", callback.from_user.id, {"product_id": product.id, "name": product.name})
    await state.clear()

    products = await products_service.list_products(data["category_id"], only_active=False)
    await callback.message.answer(
        f"✅ Товар «{product.name}» добавлен в каталог!",
        reply_markup=kb.admin_products_list_kb(products, data["category_id"]),
    )
    await callback.answer()


@router.callback_query(AdminProductFSM.confirming, F.data == "aprod_discard")
async def discard_product(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    category_id = data.get("category_id")
    await state.clear()
    await callback.message.answer("❌ Добавление товара отменено.", reply_markup=kb.admin_back_kb())
    await callback.answer()


# --------------------------------- Редактирование ---------------------------

FIELD_PROMPTS = {
    "name": "Введите новое название:",
    "price": "Введите новую цену (число):",
    "short_description": "Введите новое краткое описание:",
    "full_description": "Введите новое полное описание:",
    "characteristics": "Введите новые характеристики:",
    "stock_quantity": "Введите новое количество на складе (целое число):",
}


@router.callback_query(F.data.startswith("aprodedit:"))
async def cb_product_edit(callback: CallbackQuery, state: FSMContext) -> None:
    _, product_id, field = callback.data.split(":")
    if field == "photo":
        await state.set_state(AdminProductEditFSM.entering_value)
        await state.update_data(product_id=int(product_id), field="photo")
        await callback.message.answer("Отправьте новую фотографию товара:")
        await callback.answer()
        return
    await state.set_state(AdminProductEditFSM.entering_value)
    await state.update_data(product_id=int(product_id), field=field)
    await callback.message.answer(FIELD_PROMPTS.get(field, "Введите новое значение:"))
    await callback.answer()


@router.message(AdminProductEditFSM.entering_value, F.photo)
async def process_edit_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("field") != "photo":
        return
    await products_service.add_product_image(data["product_id"], message.photo[-1].file_id)
    await add_log("product_edited", message.from_user.id, {"product_id": data["product_id"], "field": "photo"})
    await state.clear()
    product = await products_service.get_product(data["product_id"])
    await message.answer("✅ Фотография добавлена.", reply_markup=kb.admin_product_detail_kb(product))


@router.message(AdminProductEditFSM.entering_value, F.text)
async def process_edit_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    field = data["field"]
    raw = message.text.strip()

    if field == "price":
        try:
            value = Decimal(raw.replace(",", "."))
        except InvalidOperation:
            await message.answer("Введите цену числом, например: 4990")
            return
    elif field == "stock_quantity":
        if not raw.isdigit():
            await message.answer("Введите целое число.")
            return
        value = int(raw)
    else:
        value = raw

    await products_service.update_product_field(data["product_id"], field, value)
    await add_log("product_edited", message.from_user.id, {"product_id": data["product_id"], "field": field})
    await state.clear()
    product = await products_service.get_product(data["product_id"])
    await message.answer("✅ Изменения сохранены.", reply_markup=kb.admin_product_detail_kb(product))
