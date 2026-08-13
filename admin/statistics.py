"""Статистика магазина и доход."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

import keyboards as kb
from filters import IsAdmin
from services import statistics as statistics_service
from utils import format_price, safe_edit

router = Router(name="admin_statistics")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "a_stats")
async def cb_stats(callback: CallbackQuery) -> None:
    stats = await statistics_service.dashboard_stats()
    total_sales = await format_price(stats["total_sales"])
    today_sales = await format_price(stats["today_sales"])
    week_sales = await format_price(stats["week_sales"])
    month_sales = await format_price(stats["month_sales"])

    text = (
        "📊 <b>Статистика</b>\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🟢 Активных за 24ч: {stats['active_users']}\n"
        f"📦 Всего заказов: {stats['total_orders']}\n"
        f"✅ Завершённых заказов: {stats['completed_orders']}\n"
        f"⏳ Ожидающих заказов: {stats['pending_orders']}\n"
        f"💰 Общая сумма продаж: {total_sales}\n"
        f"📈 Продажи за сегодня: {today_sales}\n"
        f"📈 Продажи за неделю: {week_sales}\n"
        f"📈 Продажи за месяц: {month_sales}"
    )
    await safe_edit(callback.message, text, reply_markup=kb.admin_stats_kb())
    await callback.answer()


@router.callback_query(F.data == "a_revenue")
async def cb_revenue(callback: CallbackQuery) -> None:
    data = await statistics_service.revenue_breakdown()
    text = (
        "💰 <b>Доход</b> (только подтверждённые/завершённые заказы)\n\n"
        f"Сегодня: {await format_price(data['today'])}\n"
        f"За 7 дней: {await format_price(data['days7'])}\n"
        f"За 30 дней: {await format_price(data['days30'])}\n"
        f"За всё время: {await format_price(data['all_time'])}"
    )
    await safe_edit(callback.message, text, reply_markup=kb.admin_revenue_kb())
    await callback.answer()
