from aiogram.fsm.state import StatesGroup, State


# ============================
# ADMIN → USER GIFT FSM
# ============================
class AdminGiftState(StatesGroup):
    waiting_for_user_id = State()


# ============================
# ADMIN → ADD ADMIN FSM
# ============================
class AdminAddState(StatesGroup):
    waiting_for_admin_id = State()


# ============================
# ADMIN → REMOVE ADMIN FSM
# ============================
class AdminRemoveState(StatesGroup):
    waiting_for_admin_id = State()


# ============================
# ADMIN → BROADCAST FSM
# ============================
class AdminBroadcastState(StatesGroup):
    waiting_for_message = State()
