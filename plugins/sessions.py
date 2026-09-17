import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db
from helpers.keyboard import (
    session_source_keyboard, cancel_keyboard, back_to_main_keyboard,
    terminate_confirm_keyboard
)
from helpers.listener import wait_for_input, cancel_input
from helpers.session_tools import get_active_sessions, terminate_all_sessions, terminate_single_session

# Temp store for active session inspection: user_id -> {"session": ..., "type": ...}
INSPECT_CACHE = {}

def detect_session_type(session_str: str) -> str:
    """Auto-detect if a string session is Telethon or Pyrogram."""
    session_str = session_str.strip()
    if session_str.startswith("1") and len(session_str) > 200:
        return "telethon"
    return "pyrogram"

@Client.on_callback_query(filters.regex("^menu_devices$"))
async def devices_menu_callback(client: Client, query: CallbackQuery):
    cancel_input(query.from_user.id)
    text = """
╭━━━━━━━━━━━━━━━━━━━━╮
│  📱 <b>ᴀᴄᴛɪᴠᴇ ᴅᴇᴠɪᴄᴇs & sᴇᴄᴜʀɪᴛʏ</b>  │
╰━━━━━━━━━━━━━━━━━━━━╯
Apne Telegram account ke active logins, devices, IP address aur locations inspect karein ya unauthorized sessions terminate karein.

Aap session string paste karna chahte hain ya apne saved vault se select karna chahte hain?
"""
    await query.message.edit_text(text, reply_markup=session_source_keyboard("devices"))

@Client.on_callback_query(filters.regex("^src_paste_devices$"))
async def paste_session_for_devices(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    await query.message.edit_text(
        "📝 <b>Please send your String Session (Pyrogram or Telethon):</b>\n\n"
        "<i>(Your session string will be deleted immediately from chat history for safety)</i>\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_keyboard()
    )
    try:
        msg = await wait_for_input(client, user_id, timeout=120)
        raw_session = msg.text.strip()
        try:
            await msg.delete()
        except Exception:
            pass
    except (asyncio.TimeoutError, ValueError):
        return

    session_type = detect_session_type(raw_session)
    await show_devices_view(client, user_id, query.message, raw_session, session_type)

@Client.on_callback_query(filters.regex("^src_vault_devices$"))
async def vault_session_for_devices(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    if not accounts:
        await query.answer("Aapke vault me koi saved account nahi hai! Pehle session add karein.", show_alert=True)
        return

    buttons = []
    for acc in accounts:
        btn_text = f"👤 {acc['account_name']} ({acc['session_type'].capitalize()})"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"seldev_acc_{acc['id']}")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_devices")])

    await query.message.edit_text(
        "💼 <b>Select an account from your Vault:</b>",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex("^seldev_acc_(\\d+)$"))
async def select_vault_account_devices(client: Client, query: CallbackQuery):
    acc_id = int(query.matches[0].group(1))
    user_id = query.from_user.id
    account = await db.get_account(acc_id, user_id)
    if not account:
        await query.answer("Account not found!", show_alert=True)
        return

    await show_devices_view(client, user_id, query.message, account["raw_session"], account["session_type"])

async def show_devices_view(client: Client, user_id: int, message: Message, raw_session: str, session_type: str):
    wait_msg = await message.reply_text("🔍 <i>Fetching active authorizations from Telegram...</i>")
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

    buttons = [
        [InlineKeyboardButton("🚨 ᴛᴇʀᴍɪɴᴀᴛᴇ ᴀʟʟ ᴏᴛʜᴇʀ sᴇssɪᴏɴs", callback_data="action_term_all")],
        [InlineKeyboardButton("🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_main")]
    ]
    await wait_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^action_term_all$"))
async def prompt_terminate_all(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in INSPECT_CACHE:
        await query.answer("Session expired from cache. Please select again!", show_alert=True)
        return

    text = """
⚠️ <b>CONFIRM TERMINATION</b> ⚠️

Kya aap sach me is session ke alawa <b>baaki sabhi devices ko logout</b> karna chahte hain?
Iske baad baaki sabhi devices se Telegram account turant band ho jayega.
"""
    await query.message.edit_text(text, reply_markup=terminate_confirm_keyboard("all"))

@Client.on_callback_query(filters.regex("^confirm_term_all$"))
async def execute_terminate_all(client: Client, query: CallbackQuery):
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
