from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db
from helpers.keyboard import (
    session_source_keyboard, cancel_keyboard, back_to_main_keyboard,
    terminate_confirm_keyboard
)
from helpers.states import DeviceStates
from helpers.session_tools import get_active_sessions, terminate_all_sessions, terminate_single_session
from handlers.common import INSPECT_CACHE, detect_session_type

router = Router()

@router.callback_query(F.data.in_(["menu_devices", "a_kill", "a_term"]))
async def cb_menu_devices(query: CallbackQuery, state: FSMContext):
    await state.clear()
    is_term = query.data == "a_term"
    title = "🚨 <b>Terminate All</b>" if is_term else "📱 <b>Kill Sessions</b>"
    text = f"""
{title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send files (<code>.session</code>, <code>.json</code>) or session string to inspect and terminate active logins.
"""
    await state.set_state(DeviceStates.waiting_session)
    await state.update_data(auto_term=is_term)
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.callback_query(F.data == "src_paste_devices")
async def cb_src_paste_devices(query: CallbackQuery, state: FSMContext):
    await state.set_state(DeviceStates.waiting_session)
    await query.message.edit_text(
        "📝 <b>Please send your String Session (Pyrogram or Telethon):</b>\n\n"
        "<i>(Your session string will be deleted immediately from chat history for safety)</i>\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_keyboard()
    )

@router.message(DeviceStates.waiting_session)
async def process_devices_session(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    raw_session = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()

    stype = detect_session_type(raw_session)
    await show_devices_view(message.from_user.id, message, raw_session, stype)

@router.callback_query(F.data == "src_vault_devices")
async def cb_src_vault_devices(query: CallbackQuery):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    if not accounts:
        await query.answer("Aapke vault me koi saved account nahi hai! Pehle session add karein.", show_alert=True)
        return

    buttons = []
    for acc in accounts:
        btn_text = f"👤 {acc['account_name']} ({acc['session_type'].capitalize()})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"seldev_acc_{acc['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="menu_devices")])

    await query.message.edit_text(
        "💼 <b>Select an account from your Vault:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("seldev_acc_"))
async def cb_select_vault_dev(query: CallbackQuery):
    acc_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    account = await db.get_account(acc_id, user_id)
    if not account:
        await query.answer("Account not found!", show_alert=True)
        return

    await show_devices_view(user_id, query.message, account["raw_session"], account["session_type"])

async def show_devices_view(user_id: int, message: Message, raw_session: str, session_type: str):
    wait_msg = await message.answer("🔍 <i>Fetching active authorizations from Telegram...</i>")
    try:
        authorizations = await get_active_sessions(raw_session, session_type)
    except Exception as e:
        await wait_msg.edit_text(f"❌ Failed to fetch sessions: <code>{e}</code>", reply_markup=back_to_main_keyboard())
        return

    if not authorizations:
        await wait_msg.edit_text("❌ No active sessions found or session is invalid/expired.", reply_markup=back_to_main_keyboard())
        return

    INSPECT_CACHE[user_id] = {
        "session": raw_session,
        "type": session_type
    }

    text = f"📱 <b>Total Active Logins:</b> <code>{len(authorizations)}</code>\n"
    text += f"⚡ <b>Engine:</b> <code>{session_type.upper()}</code>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    for idx, auth in enumerate(authorizations, start=1):
        curr_tag = " (⭐️ <b>THIS SESSION</b>)" if auth["current"] else ""
        text += (
            f"<b>{idx}. {auth['device_model']}</b>{curr_tag}\n"
            f"• <b>App:</b> <code>{auth['app_name']} {auth['app_version']}</code>\n"
            f"• <b>OS:</b> <code>{auth['platform']} {auth['system_version']}</code>\n"
            f"• <b>IP:</b> <code>{auth['ip']}</code> ({auth['country']})\n"
            f"• <b>Active:</b> <code>{auth['date_active']}</code>\n"
            "────────────────────────────\n"
        )

    buttons = []
    for idx, auth in enumerate(authorizations, start=1):
        if not auth["current"]:
            buttons.append([InlineKeyboardButton(text=f"❌ Kill {auth['device_model'][:18]}", callback_data=f"kill_single_{auth['hash']}")])
    buttons.append([InlineKeyboardButton(text="🚨 Terminate All Other Sessions", callback_data="action_term_all")])
    buttons.append([InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op")])
    await wait_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("kill_single_"))
async def cb_kill_single(query: CallbackQuery):
    auth_hash = query.data.split("_")[2]
    user_id = query.from_user.id
    if user_id not in INSPECT_CACHE:
        await query.answer("Session expired from cache. Please select again!", show_alert=True)
        return
    data = INSPECT_CACHE[user_id]
    await query.answer("Terminating device...", show_alert=False)
    success, msg = await terminate_single_session(data["session"], data["type"], int(auth_hash))
    if success:
        await query.answer("Session terminated successfully! 🗑️", show_alert=True)
        await show_devices_view(user_id, query.message, data["session"], data["type"])
    else:
        await query.answer(f"Failed: {msg}", show_alert=True)

@router.callback_query(F.data == "action_term_all")
async def cb_action_term_all(query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in INSPECT_CACHE:
        await query.answer("Session expired from cache. Please select again!", show_alert=True)
        return

    text = """
⚠️ <b>CONFIRM TERMINATION</b> ⚠️

Kya aap sach me is session ke alawa <b>baaki sabhi devices ko logout</b> karna chahte hain?
Iske baad baaki sabhi devices se Telegram account turant band ho jayega.
"""
    await query.message.edit_text(text, reply_markup=terminate_confirm_keyboard())

@router.callback_query(F.data == "confirm_term_all")
async def cb_confirm_term_all(query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in INSPECT_CACHE:
        await query.answer("Session expired from memory.", show_alert=True)
        return

    data = INSPECT_CACHE[user_id]
    await query.answer("Terminating sessions...", show_alert=False)
    status_msg = await query.message.edit_text("⏳ <i>Terminating all other active sessions...</i>")

    success, msg = await terminate_all_sessions(data["session"], data["type"])
    if success:
        await status_msg.edit_text(
            "🎉 <b>SUCCESS!</b>\n\n"
            "✅ <i>Saare dusre devices aur unauthorized sessions ko safalta-purvak terminate kar diya gaya hai!</i>\n\n"
            "🛡️ Aapka account ab surakshit hai.",
            reply_markup=back_to_main_keyboard()
        )
    else:
        await status_msg.edit_text(
            f"❌ <b>Error:</b> <code>{msg}</code>\n\n"
            "<i>Note: Agar Telegram naya login detect karta hai, to security ke kaaran kuch ghante tak terminate block kar sakta hai.</i>",
            reply_markup=back_to_main_keyboard()
        )
