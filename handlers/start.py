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

    await message.answer(
        START_TEXT.format(name=user.first_name),
        reply_markup=main_menu_keyboard(config.OWNER_ID, user.id),
        disable_web_page_preview=True
    )

@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(HELP_TEXT, reply_markup=back_to_main_keyboard(), disable_web_page_preview=True)

@router.callback_query(F.data == "back_main")
async def cb_back_main(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await cleanup_user_login(query.from_user.id)
    user = query.from_user
    await query.message.edit_text(
        START_TEXT.format(name=user.first_name),
        reply_markup=main_menu_keyboard(config.OWNER_ID, user.id),
        disable_web_page_preview=True
    )

@router.callback_query(F.data == "menu_help")
async def cb_menu_help(query: CallbackQuery):
    await query.message.edit_text(HELP_TEXT, reply_markup=back_to_main_keyboard(), disable_web_page_preview=True)

@router.callback_query(F.data == "cancel_action")
async def cb_cancel_action(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await cleanup_user_login(query.from_user.id)
    await query.answer("Operation cancelled ❌", show_alert=False)
    await query.message.edit_text(
        START_TEXT.format(name=query.from_user.first_name),
        reply_markup=main_menu_keyboard(config.OWNER_ID, query.from_user.id),
        disable_web_page_preview=True
    )
