from aiogram.fsm.state import State, StatesGroup

class GenerateStates(StatesGroup):
    waiting_fingerprint = State()
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
    waiting_spambot_session = State()
    waiting_delete_dialogs_session = State()
    waiting_2fa_session = State()
    waiting_info_session = State()
    waiting_age_session = State()
    waiting_convert_session = State()
    waiting_privacy_session = State()
    waiting_read_otp = State()
    waiting_contact = State()
    waiting_split = State()
    waiting_api_link = State()
    waiting_merge = State()
    waiting_kill_session = State()

class VCStates(StatesGroup):
    waiting_vc_msg = State()
    waiting_vc_chat = State()

class BroadcastStates(StatesGroup):
    waiting_broadcast_text = State()

class AdminStates(StatesGroup):
    waiting_broadcast_msg = State()

