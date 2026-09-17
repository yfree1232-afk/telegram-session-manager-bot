import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db
from helpers.keyboard import (
    tools_menu_keyboard, session_source_keyboard, cancel_keyboard, back_to_main_keyboard
)
from helpers.listener import wait_for_input, cancel_input
from helpers.session_tools import leave_all_dialogs, check_session_health
from plugins.sessions import detect_session_type

@Client.on_callback_query(filters.regex("^menu_tools$"))
async def tools_menu_callback(client: Client, query: CallbackQuery):
    cancel_input(query.from_user.id)
    text = """
╭━━━━━━━━━━━━━━━━━━━━╮
│  🛠 <b>ᴀᴄᴄᴏᴜɴᴛ ᴜᴛɪʟɪᴛʏ ᴛᴏᴏʟs</b>  │
╰━━━━━━━━━━━━━━━━━━━━╯
Yahan se aap apne account par batch operations kar sakte hain:

🚪 <b>Leave All Chats:</b> Saare joined channels aur groups se turant exit karein.
🔍 <b>Quick Health Check:</b> Kisi bhi string session ko paste karke check karein ki wo valid hai ya banned.
"""
    await query.message.edit_text(text, reply_markup=tools_menu_keyboard())

@Client.on_callback_query(filters.regex("^tool_leave_chats$"))
async def leave_chats_prompt(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    text = """
🚪 <b>LEAVE ALL CHANNELS & GROUPS</b>

Aap session string paste karna chahte hain ya apne saved vault se select karna chahte hain?
"""
    await query.message.edit_text(text, reply_markup=session_source_keyboard("leave"))

@Client.on_callback_query(filters.regex("^src_paste_leave$"))
async def paste_session_for_leave(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    await query.message.edit_text(
        "📝 <b>Send String Session to leave all channels & groups:</b>\n\n"
        "<i>(Session will be deleted from chat immediately)</i>\n\n"
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

    stype = detect_session_type(raw_session)
    await execute_leave_chats(client, user_id, query.message, raw_session, stype)

@Client.on_callback_query(filters.regex("^src_vault_leave$"))
async def vault_session_for_leave(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    if not accounts:
        await query.answer("Aapke vault me koi account nahi hai!", show_alert=True)
        return

    buttons = []
    for acc in accounts:
        btn_text = f"👤 {acc['account_name']} ({acc['session_type'].capitalize()})"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"selleave_acc_{acc['id']}")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_tools")])

    await query.message.edit_text("💼 <b>Select an account:</b>", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^selleave_acc_(\\d+)$"))
async def select_vault_account_leave(client: Client, query: CallbackQuery):
    acc_id = int(query.matches[0].group(1))
    user_id = query.from_user.id
    account = await db.get_account(acc_id, user_id)
    if not account:
        await query.answer("Account not found!", show_alert=True)
        return

    await execute_leave_chats(client, user_id, query.message, account["raw_session"], account["session_type"])

async def execute_leave_chats(client: Client, user_id: int, message: Message, raw_session: str, session_type: str):
    prog_msg = await message.reply_text("⏳ <i>Leaving channels and groups... This might take a few moments.</i>")
    success, res = await leave_all_dialogs(raw_session, session_type)
    if success:
        await prog_msg.edit_text(
            f"🎉 <b>CLEANUP COMPLETE!</b>\n\n✅ {res}",
            reply_markup=back_to_main_keyboard()
        )
    else:
        await prog_msg.edit_text(
            f"❌ <b>Failed:</b> <code>{res}</code>",
            reply_markup=back_to_main_keyboard()
        )

@Client.on_callback_query(filters.regex("^tool_check_health$"))
async def tool_check_health_prompt(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    await query.message.edit_text(
        "🔍 <b>QUICK SESSION HEALTH CHECK</b>\n\n"
        "Send any Pyrogram or Telethon string session to inspect its live status:\n\n"
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

    check_msg = await query.message.reply_text("🔄 <i>Testing session connection...</i>")
    stype = detect_session_type(raw_session)
    info = await check_session_health(raw_session, stype)

    if info["status"] == "alive":
        res_text = f"""
🟢 <b>SESSION IS ALIVE & ACTIVE!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Account Name:</b> {info['name']}
🆔 <b>User ID:</b> <code>{info['user_id']}</code>
📞 <b>Phone:</b> <code>{info['phone']}</code>
⚡ <b>Detected Type:</b> <code>{stype.upper()}</code>
🌐 <b>DC ID:</b> {info['dc_id']}
💎 <b>Premium:</b> {'Yes ⭐️' if info['is_premium'] else 'No'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    else:
        res_text = f"""
🔴 <b>SESSION IS DEAD / REVOKED!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>Reason:</b> <code>{info['error']}</code>
⚡ <b>Detected Type:</b> <code>{stype.upper()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await check_msg.edit_text(res_text, reply_markup=back_to_main_keyboard())
