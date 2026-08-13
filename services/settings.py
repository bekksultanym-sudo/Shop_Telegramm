"""
Настройки магазина, редактируемые через админ-панель (без изменения кода).
"""
from __future__ import annotations

from sqlalchemy import select

from database import get_session
from models import Setting

DEFAULTS: dict[str, str] = {
    "shop_name": "Наш магазин",
    "shop_description": "Лучшие товары с быстрой доставкой.",
    "welcome_text": (
        "👋 Добро пожаловать в наш магазин!\n\n"
        "Здесь вы можете ознакомиться с каталогом товаров, оформить заказ "
        "и получить помощь поддержки."
    ),
    "currency": "₸",
    "btn_catalog": "🛍 Каталог",
    "btn_reviews": "⭐ Отзывы",
    "btn_support": "🆘 Техподдержка",
    "btn_profile": "👤 Профиль",
    "btn_orders": "📦 Мои заказы",
    "support_username": "",
}

_cache: dict[str, str] | None = None


async def _load_all() -> dict[str, str]:
    global _cache
    async with get_session() as session:
        result = await session.execute(select(Setting))
        rows = result.scalars().all()
        data = dict(DEFAULTS)
        for row in rows:
            data[row.key] = row.value
        _cache = data
        return data


async def get(key: str) -> str:
    global _cache
    if _cache is None:
        await _load_all()
    assert _cache is not None
    return _cache.get(key, DEFAULTS.get(key, ""))


async def get_all() -> dict[str, str]:
    if _cache is None:
        return await _load_all()
    return dict(_cache)


async def set(key: str, value: str) -> None:
    global _cache
    async with get_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == key))
        row = result.scalar_one_or_none()
        if row is None:
            row = Setting(key=key, value=value)
            session.add(row)
        else:
            row.value = value
        await session.commit()
    if _cache is not None:
        _cache[key] = value
    else:
        await _load_all()
