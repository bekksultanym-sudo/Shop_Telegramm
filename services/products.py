"""Бизнес-логика каталога: категории и товары."""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from database import get_session
from models import Category, Product, ProductImage, ProductVariant


async def list_categories(only_active: bool = True) -> list[Category]:
    async with get_session() as session:
        stmt = select(Category).order_by(Category.sort_order, Category.id)
        if only_active:
            stmt = stmt.where(Category.is_active.is_(True))
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_category(category_id: int) -> Category | None:
    async with get_session() as session:
        return await session.get(Category, category_id)


async def create_category(name: str) -> Category:
    async with get_session() as session:
        result = await session.execute(select(Category.sort_order).order_by(Category.sort_order.desc()).limit(1))
        max_order = result.scalar_one_or_none() or 0
        category = Category(name=name, sort_order=max_order + 1)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        return category


async def rename_category(category_id: int, new_name: str) -> None:
    async with get_session() as session:
        await session.execute(update(Category).where(Category.id == category_id).values(name=new_name))
        await session.commit()


async def toggle_category(category_id: int) -> None:
    async with get_session() as session:
        category = await session.get(Category, category_id)
        if category:
            category.is_active = not category.is_active
            await session.commit()


async def delete_category(category_id: int) -> None:
    async with get_session() as session:
        category = await session.get(Category, category_id)
        if category:
            await session.delete(category)
            await session.commit()


async def move_category(category_id: int, direction: int) -> None:
    """direction: -1 (выше) or +1 (ниже)."""
    async with get_session() as session:
        categories = list(
            (await session.execute(select(Category).order_by(Category.sort_order, Category.id))).scalars().all()
        )
        idx = next((i for i, c in enumerate(categories) if c.id == category_id), None)
        if idx is None:
            return
        swap_idx = idx + direction
        if 0 <= swap_idx < len(categories):
            categories[idx].sort_order, categories[swap_idx].sort_order = (
                categories[swap_idx].sort_order,
                categories[idx].sort_order,
            )
            await session.commit()


async def list_products(category_id: int, only_active: bool = True) -> list[Product]:
    async with get_session() as session:
        stmt = select(Product).where(Product.category_id == category_id).order_by(Product.id)
        if only_active:
            stmt = stmt.where(Product.is_active.is_(True))
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_product(product_id: int) -> Product | None:
    async with get_session() as session:
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.images), selectinload(Product.variants))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def create_product(**fields) -> Product:
    async with get_session() as session:
        product = Product(**fields)
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product


async def add_product_image(product_id: int, file_id: str, sort_order: int = 0) -> None:
    async with get_session() as session:
        session.add(ProductImage(product_id=product_id, file_id=file_id, sort_order=sort_order))
        await session.commit()


async def add_product_variant(product_id: int, name: str, price_modifier=0, stock_quantity: int = 0) -> None:
    async with get_session() as session:
        session.add(
            ProductVariant(
                product_id=product_id, name=name, price_modifier=price_modifier, stock_quantity=stock_quantity
            )
        )
        await session.commit()


async def update_product_field(product_id: int, field: str, value) -> None:
    allowed = {
        "name",
        "price",
        "short_description",
        "full_description",
        "characteristics",
        "stock_quantity",
    }
    if field not in allowed:
        raise ValueError(f"Field {field} is not editable")
    async with get_session() as session:
        await session.execute(update(Product).where(Product.id == product_id).values(**{field: value}))
        await session.commit()


async def toggle_product(product_id: int) -> None:
    async with get_session() as session:
        product = await session.get(Product, product_id)
        if product:
            product.is_active = not product.is_active
            await session.commit()

async def delete_product(product_id: int) -> bool:
    """Удаляет товар. True — удалён полностью, False — скрыт вместо
    удаления (на него ссылаются существующие заказы)."""
    from sqlalchemy.exc import IntegrityError

    async with get_session() as session:
        product = await session.get(Product, product_id)
        if not product:
            return True
        try:
            await session.delete(product)
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()

    async with get_session() as session:
        product = await session.get(Product, product_id)
        if product:
            product.is_active = False
            await session.commit()
    return False

