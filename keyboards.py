"""Inline-клавиатуры для пользовательской части и админ-панели."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models import Category, Order, PaymentMethod, Product, ProductVariant, OrderStatus, User

# ---------------------------------------------------------------------------
# Общие
# ---------------------------------------------------------------------------

BACK = "⬅️ Назад"
HOME = "🏠 Главное меню"
CANCEL = "❌ Отмена"


def nav_row(back_cb: str | None = None, home: bool = True) -> list[InlineKeyboardButton]:
    row = []
    if back_cb:
        row.append(InlineKeyboardButton(text=BACK, callback_data=back_cb))
    if home:
        row.append(InlineKeyboardButton(text=HOME, callback_data="home"))
    return row


def main_menu(labels: dict[str, str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=labels["btn_catalog"], callback_data="catalog")
    kb.button(text=labels["btn_reviews"], callback_data="reviews")
    kb.button(text=labels["btn_support"], callback_data="support")
    kb.button(text=labels["btn_profile"], callback_data="profile")
    kb.button(text=labels["btn_orders"], callback_data="my_orders")
    kb.adjust(1)
    return kb.as_markup()


def categories_kb(categories: list[Category]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in categories:
        kb.button(text=c.name, callback_data=f"cat:{c.id}")
    kb.adjust(2)
    kb.row(*nav_row(home=True))
    return kb.as_markup()


def products_kb(products: list[Product], category_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        kb.button(text=p.name, callback_data=f"prod:{p.id}")
    kb.adjust(1)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"catpage:{category_id}:{page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"catpage:{category_id}:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.row(*nav_row(back_cb="catalog"))
    return kb.as_markup()


def product_card_kb(product: Product, photo_index: int, photo_count: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if photo_count > 1:
        kb.row(
            InlineKeyboardButton(text="◀", callback_data=f"prodphoto:{product.id}:{photo_index-1}"),
            InlineKeyboardButton(text=f"{photo_index+1}/{photo_count}", callback_data="noop"),
            InlineKeyboardButton(text="▶", callback_data=f"prodphoto:{product.id}:{photo_index+1}"),
        )
    if product.stock_quantity > 0:
        kb.row(InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy:{product.id}"))
    else:
        kb.row(InlineKeyboardButton(text="⛔️ Нет в наличии", callback_data="noop"))
    kb.row(*nav_row(back_cb=f"cat:{product.category_id}"))
    return kb.as_markup()


def variants_kb(product_id: int, variants: list[ProductVariant]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for v in variants:
        kb.button(text=v.name, callback_data=f"variant:{product_id}:{v.id}")
    kb.adjust(1)
    kb.row(*nav_row(back_cb=f"prod:{product_id}"))
    return kb.as_markup()


def quantity_kb(product_id: int, qty: int, max_qty: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="➖", callback_data=f"qty:{product_id}:{max(1, qty-1)}"),
        InlineKeyboardButton(text=str(qty), callback_data="noop"),
        InlineKeyboardButton(text="➕", callback_data=f"qty:{product_id}:{min(max_qty, qty+1)}"),
    )
    kb.row(InlineKeyboardButton(text="✅ Далее", callback_data=f"qtyconfirm:{product_id}:{qty}"))
    kb.row(*nav_row(back_cb=f"prod:{product_id}"))
    return kb.as_markup()


def order_summary_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💳 Перейти к оплате", callback_data="order_pay"))
    kb.row(InlineKeyboardButton(text=CANCEL, callback_data="order_cancel"))
    return kb.as_markup()


def payment_methods_kb(methods: list[PaymentMethod]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for m in methods:
        kb.button(text=m.name, callback_data=f"paymethod:{m.id}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text=CANCEL, callback_data="order_cancel"))
    return kb.as_markup()


def after_payment_details_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🧾 Я оплатил, отправить чек", callback_data="send_receipt"))
    kb.row(InlineKeyboardButton(text=CANCEL, callback_data="order_cancel"))
    return kb.as_markup()


def admin_order_review_kb(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"aorder_confirm:{order_id}"),
        InlineKeyboardButton(text="❌ Отклонить оплату", callback_data=f"aorder_reject:{order_id}"),
    )
    return kb.as_markup()


def my_orders_kb(orders: list[Order]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for o in orders:
        kb.button(text=f"📦 Заказ №{o.id} — {o.status.value}", callback_data=f"myorder:{o.id}")
    kb.adjust(1)
    kb.row(*nav_row(home=True))
    return kb.as_markup()


def order_detail_kb(order_id: int, can_cancel: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if can_cancel:
        kb.row(InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"cancel_order:{order_id}"))
    kb.row(*nav_row(back_cb="my_orders", home=True))
    return kb.as_markup()


def support_kb(operators: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for op in operators:
        kb.button(text=f"👤 {op.label or op.username}", url=f"https://t.me/{op.username}")
    kb.adjust(1)
    kb.row(*nav_row(home=True))
    return kb.as_markup()


def back_home_kb(back_cb: str | None = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(*nav_row(back_cb=back_cb, home=True))
    return kb.as_markup()


def confirm_kb(yes_cb: str, no_cb: str, yes_text: str = "✅ Подтвердить", no_text: str = CANCEL) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text=yes_text, callback_data=yes_cb),
        InlineKeyboardButton(text=no_text, callback_data=no_cb),
    )
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Админ-панель
# ---------------------------------------------------------------------------

def admin_main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    items = [
        ("📊 Статистика", "a_stats"),
        ("📦 Заказы", "a_orders"),
        ("🛍 Товары", "a_products"),
        ("📁 Категории", "a_categories"),
        ("💳 Оплата", "a_payments"),
        ("⭐ Отзывы", "a_reviews"),
        ("🆘 Техподдержка", "a_support"),
        ("📢 Рассылка", "a_broadcast"),
        ("👥 Пользователи", "a_users"),
        ("🚫 Бан / Разбан", "a_ban"),
        ("👑 Администраторы", "a_admins"),
        ("📜 Логи", "a_logs"),
        ("💰 Доход", "a_revenue"),
        ("⚙️ Настройки", "a_settings"),
    ]
    for text, cb in items:
        kb.button(text=text, callback_data=cb)
    kb.adjust(2)
    return kb.as_markup()


def admin_back_kb(back_cb: str = "admin_home") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data=back_cb))
    return kb.as_markup()


def admin_categories_kb(categories: list[Category]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in categories:
        status = "✅" if c.is_active else "🚫"
        kb.button(text=f"{status} {c.name}", callback_data=f"acat:{c.id}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="➕ Добавить категорию", callback_data="acat_add"))
    kb.row(*[b for b in admin_back_kb().inline_keyboard[0]])
    return kb.as_markup()


def admin_category_detail_kb(category: Category) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"acat_rename:{category.id}"))
    toggle = "🚫 Скрыть" if category.is_active else "✅ Включить"
    kb.row(InlineKeyboardButton(text=toggle, callback_data=f"acat_toggle:{category.id}"))
    kb.row(InlineKeyboardButton(text="⬆️ Выше", callback_data=f"acat_up:{category.id}"),
           InlineKeyboardButton(text="⬇️ Ниже", callback_data=f"acat_down:{category.id}"))
    kb.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"acat_delete:{category.id}"))
    kb.row(InlineKeyboardButton(text=BACK, callback_data="a_categories"))
    return kb.as_markup()


def admin_products_list_kb(products: list[Product], category_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        status = "✅" if p.is_active else "🚫"
        kb.button(text=f"{status} {p.name}", callback_data=f"aprod:{p.id}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"aprod_add:{category_id}"))
    kb.row(InlineKeyboardButton(text=BACK, callback_data="a_products"))
    return kb.as_markup()


def admin_product_detail_kb(product: Product) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Название", callback_data=f"aprodedit:{product.id}:name")
    kb.button(text="💰 Цена", callback_data=f"aprodedit:{product.id}:price")
    kb.button(text="📝 Краткое описание", callback_data=f"aprodedit:{product.id}:short_description")
    kb.button(text="📄 Полное описание", callback_data=f"aprodedit:{product.id}:full_description")
    kb.button(text="📋 Характеристики", callback_data=f"aprodedit:{product.id}:characteristics")
    kb.button(text="📦 Количество", callback_data=f"aprodedit:{product.id}:stock_quantity")
    kb.button(text="🖼 Добавить фото", callback_data=f"aprodedit:{product.id}:photo")
    kb.adjust(2)
    toggle = "🚫 Скрыть" if product.is_active else "✅ Вернуть в продажу"
    kb.row(InlineKeyboardButton(text=toggle, callback_data=f"aprod_toggle:{product.id}"))
    kb.row(InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"aprod_delete:{product.id}"))
    kb.row(InlineKeyboardButton(text=BACK, callback_data=f"a_products_cat:{product.category_id}"))
    return kb.as_markup()


def admin_categories_pick_kb(categories: list[Category], prefix: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in categories:
        kb.button(text=c.name, callback_data=f"{prefix}:{c.id}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text=CANCEL, callback_data="a_products"))
    return kb.as_markup()


def admin_orders_filter_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    labels = {
        OrderStatus.NEW: "🆕 Новые",
        OrderStatus.WAITING_PAYMENT: "⏳ Ждут оплаты",
        OrderStatus.PAYMENT_CHECK: "🧾 Ждут проверки",
        OrderStatus.PAID: "💰 Оплаченные",
        OrderStatus.PROCESSING: "⚙️ В обработке",
        OrderStatus.SHIPPED: "🚚 Отправленные",
        OrderStatus.COMPLETED: "✅ Завершённые",
        OrderStatus.CANCELLED: "❌ Отменённые",
    }
    for status, text in labels.items():
        kb.button(text=text, callback_data=f"aordersf:{status.value}:0")
    kb.adjust(2)
    kb.row(InlineKeyboardButton(text=BACK, callback_data="admin_home"))
    return kb.as_markup()


def admin_orders_list_kb(orders: list[Order], status: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for o in orders:
        kb.button(text=f"№{o.id} — {o.total_amount}", callback_data=f"aorder:{o.id}")
    kb.adjust(1)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"aordersf:{status}:{page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"aordersf:{status}:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text=BACK, callback_data="a_orders"))
    return kb.as_markup()


def admin_order_status_kb(order: Order) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    transitions = {
        OrderStatus.PAID: [("⚙️ В обработку", OrderStatus.PROCESSING)],
        OrderStatus.PROCESSING: [("🚚 Отправлен", OrderStatus.SHIPPED)],
        OrderStatus.SHIPPED: [("✅ Завершить", OrderStatus.COMPLETED)],
    }
    for text, new_status in transitions.get(order.status, []):
        kb.button(text=text, callback_data=f"aorder_status:{order.id}:{new_status.value}")
    kb.adjust(1)
    if order.status not in (OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
        kb.row(InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"aorder_status:{order.id}:{OrderStatus.CANCELLED.value}"))
    kb.row(InlineKeyboardButton(text=BACK, callback_data="a_orders"))
    return kb.as_markup()


def admin_payments_kb(methods: list[PaymentMethod]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for m in methods:
        status = "✅" if m.is_active else "🚫"
        kb.button(text=f"{status} {m.name}", callback_data=f"apay:{m.id}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="➕ Добавить способ оплаты", callback_data="apay_add"))
    kb.row(InlineKeyboardButton(text=BACK, callback_data="admin_home"))
    return kb.as_markup()


def admin_payment_detail_kb(method: PaymentMethod) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    toggle = "🚫 Скрыть" if method.is_active else "✅ Включить"
    kb.row(InlineKeyboardButton(text=toggle, callback_data=f"apay_toggle:{method.id}"))
    kb.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"apay_delete:{method.id}"))
    kb.row(InlineKeyboardButton(text=BACK, callback_data="a_payments"))
    return kb.as_markup()


def admin_reviews_kb(reviews: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for r in reviews:
        mark = "📌" if r.is_pinned else ("✅" if r.is_published else "🕓")
        kb.button(text=f"{mark} #{r.id} — {(r.text or '')[:20]}", callback_data=f"arev:{r.id}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text=BACK, callback_data="admin_home"))
    return kb.as_markup()


def admin_review_detail_kb(review) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if review.is_published:
        kb.button(text="🙈 Скрыть", callback_data=f"arev_hide:{review.id}")
    else:
        kb.button(text="✅ Опубликовать", callback_data=f"arev_publish:{review.id}")
    pin_text = "📌 Открепить" if review.is_pinned else "📌 Закрепить"
    kb.button(text=pin_text, callback_data=f"arev_pin:{review.id}")
    kb.button(text="🗑 Удалить", callback_data=f"arev_delete:{review.id}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text=BACK, callback_data="a_reviews"))
    return kb.as_markup()


def admin_support_kb(operators: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for op in operators:
        status = "✅" if op.is_active else "🚫"
        kb.button(text=f"{status} @{op.username}", callback_data=f"asup:{op.id}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="➕ Добавить оператора", callback_data="asup_add"))
    kb.row(InlineKeyboardButton(text=BACK, callback_data="admin_home"))
    return kb.as_markup()


def admin_support_detail_kb(op) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    toggle = "🚫 Скрыть" if op.is_active else "✅ Включить"
    kb.row(InlineKeyboardButton(text=toggle, callback_data=f"asup_toggle:{op.id}"))
    kb.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"asup_delete:{op.id}"))
    kb.row(InlineKeyboardButton(text=BACK, callback_data="a_support"))
    return kb.as_markup()


def admin_broadcast_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="abroadcast_send"),
        InlineKeyboardButton(text=CANCEL, callback_data="abroadcast_cancel"),
    )
    return kb.as_markup()


def admin_users_list_kb(users: list[User], page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for u in users:
        label = f"@{u.username}" if u.username else (u.full_name or str(u.tg_id))
        kb.button(text=label, callback_data=f"auser:{u.tg_id}")
    kb.adjust(1)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"ausers:{page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"ausers:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text=BACK, callback_data="admin_home"))
    return kb.as_markup()


def admin_user_detail_kb(user) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if user.is_banned:
        kb.row(InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"auser_unban:{user.tg_id}"))
    else:
        kb.row(InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"auser_ban:{user.tg_id}"))
    kb.row(InlineKeyboardButton(text=BACK, callback_data="a_users"))
    return kb.as_markup()


def admin_admins_kb(admins: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for a in admins:
        kb.button(text=f"{a.role.value} — {a.username or a.tg_id}", callback_data=f"aadmin:{a.tg_id}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="➕ Добавить администратора", callback_data="aadmin_add"))
    kb.row(InlineKeyboardButton(text=BACK, callback_data="admin_home"))
    return kb.as_markup()


def admin_admin_detail_kb(admin) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➖ Удалить администратора", callback_data=f"aadmin_remove:{admin.tg_id}"))
    kb.row(InlineKeyboardButton(text=BACK, callback_data="a_admins"))
    return kb.as_markup()


def admin_role_pick_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="SUPER_ADMIN", callback_data="aadmin_role:SUPER_ADMIN")
    kb.button(text="ADMIN", callback_data="aadmin_role:ADMIN")
    kb.button(text="SUPPORT", callback_data="aadmin_role:SUPPORT")
    kb.adjust(1)
    return kb.as_markup()


def admin_settings_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    items = [
        ("Название магазина", "shop_name"),
        ("Описание магазина", "shop_description"),
        ("Приветственный текст", "welcome_text"),
        ("Валюта", "currency"),
        ("Кнопка «Каталог»", "btn_catalog"),
        ("Кнопка «Отзывы»", "btn_reviews"),
        ("Кнопка «Техподдержка»", "btn_support"),
        ("Кнопка «Профиль»", "btn_profile"),
        ("Кнопка «Мои заказы»", "btn_orders"),
    ]
    for text, key in items:
        kb.button(text=text, callback_data=f"aset:{key}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text=BACK, callback_data="admin_home"))
    return kb.as_markup()


def admin_revenue_kb() -> InlineKeyboardMarkup:
    return admin_back_kb("admin_home")


def admin_stats_kb() -> InlineKeyboardMarkup:
    return admin_back_kb("admin_home")


def admin_logs_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"alogs:{page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"alogs:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text=BACK, callback_data="admin_home"))
    return kb.as_markup()
