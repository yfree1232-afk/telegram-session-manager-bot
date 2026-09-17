from aiogram.fsm.state import State, StatesGroup

class GenerateStates(StatesGroup):
    waiting_custom_api_id = State()
    waiting_custom_api_hash = State()
    waiting_phone = State()
    waiting_otp = State()
    waiting_2fa = State()

class DeviceStates(StatesGroup):
    waiting_session = State()

class VaultStates(StatesGroup):
    waiting_session = State()

class ToolStates(StatesGroup):
    waiting_leave_session = State()
    waiting_health_session = State()

class AdminStates(StatesGroup):
    waiting_broadcast_msg = State()
