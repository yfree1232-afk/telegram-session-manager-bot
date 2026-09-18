from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
import config
from database.db import db
from helpers.keyboard import main_menu_keyboard, back_to_main_keyboard
from handlers.common import START_TEXT, HELP_TEXT, cleanup_user_login

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await cleanup_user_login(message.from_user.id)
    user = message.from_user
    await db.add_user(user.id, user.first_name, user.username)
    acc_count = await db.count_user_accounts(user.id)

    await message.answer(
        START_TEXT,
        reply_markup=main_menu_keyboard(config.OWNER_ID, user.id, acc_count),
        disable_web_page_preview=True
    )

@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(HELP_TEXT, reply_markup=back_to_main_keyboard(), disable_web_page_preview=True)

@router.message(Command("generate"))
async def cmd_generate(message: Message, state: FSMContext):
    from handlers.generate import cb_menu_generate
    class MockQuery:
        def __init__(self, msg):
            self.message = msg
            self.from_user = msg.from_user
            self.data = "menu_generate"
        async def answer(self, *args, **kwargs):
            pass
    await cb_menu_generate(MockQuery(message), state)

@router.message(Command("devices"))
async def cmd_devices(message: Message, state: FSMContext):
    from handlers.devices import cb_menu_devices
    class MockQuery:
        def __init__(self, msg):
            self.message = msg
            self.from_user = msg.from_user
            self.data = "menu_devices"
        async def answer(self, *args, **kwargs):
            pass
    await cb_menu_devices(MockQuery(message), state)

@router.message(Command("accounts"))
@router.message(Command("vault"))
async def cmd_vault(message: Message, state: FSMContext):
    from handlers.vault import cb_menu_vault
    class MockQuery:
        def __init__(self, msg):
            self.message = msg
            self.from_user = msg.from_user
            self.data = "menu_vault"
        async def answer(self, *args, **kwargs):
            pass
    await cb_menu_vault(MockQuery(message), state)

@router.message(Command("tools"))
async def cmd_tools(message: Message, state: FSMContext):
    from handlers.tools import cb_menu_tools
    class MockQuery:
        def __init__(self, msg):
            self.message = msg
            self.from_user = msg.from_user
            self.data = "menu_tools"
        async def answer(self, *args, **kwargs):
            pass
    await cb_menu_tools(MockQuery(message), state)

@router.callback_query(F.data.in_(["back_main", "cancel_action", "cancel_pending_op"]))
async def cb_back_main(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await cleanup_user_login(query.from_user.id)
    user = query.from_user
    acc_count = await db.count_user_accounts(user.id)
    try:
        await query.answer()
    except Exception:
        pass
    try:
        await query.message.edit_text(
            START_TEXT,
            reply_markup=main_menu_keyboard(config.OWNER_ID, user.id, acc_count),
            disable_web_page_preview=True
        )
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.answer(
            START_TEXT,
            reply_markup=main_menu_keyboard(config.OWNER_ID, user.id, acc_count),
            disable_web_page_preview=True
        )

