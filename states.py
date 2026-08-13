"""FSM-состояния для пользовательской части и админ-панели."""
from aiogram.fsm.state import State, StatesGroup


# --------------------------- Пользователь ---------------------------------

class OrderFSM(StatesGroup):
    choosing_variant = State()
    choosing_quantity = State()
    entering_address = State()
    choosing_payment = State()
    uploading_receipt = State()


class ReviewFSM(StatesGroup):
    entering_text = State()
    entering_rating = State()


class SupportFSM(StatesGroup):
    entering_message = State()


# ----------------------------- Админка -------------------------------------

class AdminProductFSM(StatesGroup):
    choosing_category = State()
    entering_name = State()
    uploading_photo = State()
    uploading_more_photos = State()
    entering_price = State()
    entering_short_description = State()
    entering_full_description = State()
    entering_characteristics = State()
    entering_quantity = State()
    entering_variants = State()
    confirming = State()


class AdminProductEditFSM(StatesGroup):
    choosing_field = State()
    entering_value = State()


class AdminCategoryFSM(StatesGroup):
    entering_name = State()
    entering_new_name = State()


class AdminPaymentMethodFSM(StatesGroup):
    entering_name = State()
    entering_details = State()
    entering_instructions = State()


class AdminBanFSM(StatesGroup):
    entering_tg_id = State()
    entering_reason = State()


class AdminAdminsFSM(StatesGroup):
    entering_tg_id = State()
    choosing_role = State()
    entering_remove_id = State()


class AdminBroadcastFSM(StatesGroup):
    composing = State()
    confirming = State()


class AdminSettingsFSM(StatesGroup):
    entering_value = State()


class AdminSupportFSM(StatesGroup):
    entering_username = State()
    entering_label = State()


class AdminOrderFSM(StatesGroup):
    entering_reject_reason = State()
