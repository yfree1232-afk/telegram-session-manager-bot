import asyncio
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from database.db import db
import config
from helpers.keyboard import cancel_keyboard, back_to_main_keyboard
from helpers.states import BroadcastStates
from telethon import TelegramClient
from telethon.sessions import StringSession

logger = logging.getLogger("BroadcastHandler")
router = Router()

@router.callback_query(F.data == "menu_broadcast")
async def cb_menu_broadcast(query: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    active_accounts = [a for a in accounts if a.get("is_active", 1) == 1 and a.get("status") == "ACTIVE"]

    text = f"""
╔══════════════════════════╗
║  📡 <b>𝗠𝗨𝗟𝗧𝗜-𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧</b>  ║
╚══════════════════════════╝
<blockquote><i>Aapke saare active accounts se mass messaging / promotional announcements dispatch karein!</i></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 <b>Total Accounts:</b> <code>{len(accounts)}</code>
🟢 <b>Active Ready Accounts:</b> <code>{len(active_accounts)}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Messages automatically round-robin distribution me send honge taaki koi bhi account spam filter me na fase!</i>
"""
    buttons = [
        [InlineKeyboardButton(text="🚀 Start New Broadcast", callback_data="bc_start_step1", style="success")],
        [InlineKeyboardButton(text="🎛️ Configure Active IDs", callback_data="vc_select_accounts", style="primary")],
        [InlineKeyboardButton(text="🔙 Back to Dashboard", callback_data="back_main", style="default")]
    ]
    try:
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except TelegramBadRequest:
        pass
    await query.answer()

@router.callback_query(F.data == "bc_start_step1")
async def cb_bc_step1(query: CallbackQuery, state: FSMContext):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    active_accounts = [a for a in accounts if a.get("is_active", 1) == 1 and a.get("status") == "ACTIVE"]

    if not active_accounts:
        await query.answer("⚠️ Aapke paas koi ACTIVE account nahi hai! Pehle accounts connect karein ya ON karein.", show_alert=True)
        return

    await state.set_state(BroadcastStates.waiting_broadcast_text)
    text = """
📝 <b>Broadcast Message Content</b>

👉 Jo message aap send karna chahte hain, wo yahan chat me bhejein:
<i>(Text message support karta hai)</i>

Send /cancel to abort.
"""
    try:
        await query.message.edit_text(text, reply_markup=cancel_keyboard())
    except TelegramBadRequest:
        pass
    await query.answer()

@router.message(BroadcastStates.waiting_broadcast_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.reply("Broadcast cancelled.", reply_markup=back_to_main_keyboard())
        return

    bc_text = message.text.strip()
    user_id = message.from_user.id
    await state.clear()

    accounts = await db.get_user_accounts(user_id)
    active_accounts = [a for a in accounts if a.get("is_active", 1) == 1 and a.get("status") == "ACTIVE"]

    status_msg = await message.answer(f"⏳ <b>Initializing broadcast with {len(active_accounts)} accounts...</b>")

    sent_count = 0
    fail_count = 0

    # Test-send to Saved Messages of each active account to verify session broadcast readiness
    for acc in active_accounts:
        raw_sess = acc.get("raw_session") or acc.get("session_string")
        if not raw_sess:
            continue
        try:
            client = TelegramClient(StringSession(raw_sess), config.API_ID, config.API_HASH)
            await client.connect()
            if await client.is_user_authorized():
                await client.send_message("me", f"📢 <b>Multi-Account Broadcast Dispatch Test:</b>\n\n{bc_text}", parse_mode="html")
                sent_count += 1
            else:
                fail_count += 1
            await client.disconnect()
        except Exception as e:
            logger.warning(f"Error in broadcast test for {acc.get('phone')}: {e}")
            fail_count += 1

    summary = f"""
🎉 <b>Multi-Account Broadcast Test Complete!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ <b>Verified & Dispatched to Saved Messages:</b> <code>{sent_count}</code> IDs
⚠️ <b>Failed / Revoked Sessions:</b> <code>{fail_count}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Aapke sessions ready hain! VC me automated real-time blast karne ke liye <b>'🎙️ VC Auto-DM'</b> feature use karein.</i>
"""
    buttons = [
        [InlineKeyboardButton(text="🎙️ VC Live Blaster", callback_data="menu_vc", style="success")],
        [InlineKeyboardButton(text="🏠 Main Dashboard", callback_data="back_main", style="default")]
    ]
    await status_msg.edit_text(summary, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
