import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db
from helpers.keyboard import cancel_keyboard, back_to_main_keyboard
from helpers.listener import wait_for_input, cancel_input
import config

@Client.on_callback_query(filters.regex("^admin_panel$"))
async def admin_panel_callback(client: Client, query: CallbackQuery):
    if query.from_user.id != config.OWNER_ID:
        await query.answer("Access Denied ❌", show_alert=True)
        return

    users_count = await db.get_users_count()
    text = f"""
👑 <b>ADMIN CONTROL PANEL</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 <b>Total Bot Users:</b> <code>{users_count}</code>
🤖 <b>Bot Token ID:</b> <code>{config.BOT_TOKEN.split(':')[0]}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    buttons = [
        [InlineKeyboardButton("📢 ʙʀᴏᴀᴅᴄᴀsᴛ ᴍᴇssᴀɢᴇ", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_main")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^admin_broadcast$"))
async def admin_broadcast_prompt(client: Client, query: CallbackQuery):
    if query.from_user.id != config.OWNER_ID:
        return

    await query.message.edit_text(
        "📢 <b>Enter the message you want to broadcast to all users:</b>\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_keyboard()
    )
    try:
        msg = await wait_for_input(client, query.from_user.id, timeout=120)
    except (asyncio.TimeoutError, ValueError):
        return

    status_msg = await msg.reply_text("🔄 <i>Broadcasting in progress...</i>")
    user_ids = await db.get_all_users()

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await msg.copy(chat_id=uid)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ <b>Broadcast Complete!</b>\n\n"
        f"📤 <b>Sent:</b> {sent}\n"
        f"❌ <b>Failed / Blocked:</b> {failed}",
        reply_markup=back_to_main_keyboard()
    )

@Client.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    if message.from_user.id != config.OWNER_ID:
        return
    count = await db.get_users_count()
    await message.reply_text(f"📊 <b>Total Users:</b> <code>{count}</code>")
