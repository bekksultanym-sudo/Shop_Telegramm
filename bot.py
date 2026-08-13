"""Точка входа: запуск Telegram-бота."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from config import config
from database import init_models
from middleware import BanCheckMiddleware

from handlers import start as h_start
from handlers import catalog as h_catalog
from handlers import products as h_products
from handlers import cart as h_cart
from handlers import orders as h_orders
from handlers import payment as h_payment
from handlers import reviews as h_reviews
from handlers import support as h_support
from handlers import profile as h_profile

from admin import dashboard as a_dashboard
from admin import products as a_products
from admin import categories as a_categories
from admin import orders as a_orders
from admin import users as a_users
from admin import payments as a_payments
from admin import reviews as a_reviews
from admin import support as a_support
from admin import broadcast as a_broadcast
from admin import statistics as a_statistics
from admin import admins as a_admins
from admin import logs as a_logs
from admin import settings as a_settings

logging.basicConfig(level=config.log_level)
logger = logging.getLogger(__name__)


async def _bootstrap_super_admins() -> None:
    """Гарантирует, что ID из SUPER_ADMIN_IDS есть в таблице admins с ролью SUPER_ADMIN."""
    from models import AdminRole
    from services import admins as admins_service

    existing_ids = set(await admins_service.list_admin_tg_ids())
    for tg_id in config.super_admin_ids:
        if tg_id not in existing_ids:
            await admins_service.add_admin(tg_id, username=None, role=AdminRole.SUPER_ADMIN, added_by=None)
            logger.info("Bootstrapped super admin %s", tg_id)


async def main() -> None:
    await init_models()
    await _bootstrap_super_admins()

    storage = RedisStorage.from_url(config.redis_url)
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())

    # --- Пользовательская часть ---
    dp.include_router(h_start.router)
    dp.include_router(h_catalog.router)
    dp.include_router(h_products.router)
    dp.include_router(h_cart.router)
    dp.include_router(h_orders.router)
    dp.include_router(h_payment.router)
    dp.include_router(h_reviews.router)
    dp.include_router(h_support.router)
    dp.include_router(h_profile.router)

    # --- Админ-панель (регистрируется отдельно, доступ проверяется фильтром) ---
    dp.include_router(a_dashboard.router)
    dp.include_router(a_products.router)
    dp.include_router(a_categories.router)
    dp.include_router(a_orders.router)
    dp.include_router(a_users.router)
    dp.include_router(a_payments.router)
    dp.include_router(a_reviews.router)
    dp.include_router(a_support.router)
    dp.include_router(a_broadcast.router)
    dp.include_router(a_statistics.router)
    dp.include_router(a_admins.router)
    dp.include_router(a_logs.router)
    dp.include_router(a_settings.router)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
