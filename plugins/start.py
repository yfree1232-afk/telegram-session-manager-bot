from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from database.db import db
from helpers.keyboard import main_menu_keyboard, back_to_main_keyboard
from helpers.listener import cancel_input
import config

START_TEXT = """
╔══════════════════════════╗
║  ⚡ <b>𝗦𝗘𝗦𝗦𝗜𝗢𝗡 𝗠𝗔𝗡𝗔𝗚𝗘𝗥 𝗩𝗢𝗟𝗧𝗫</b> ⚡  ║
╚══════════════════════════╝
👋 <b>Welcome, {name}!</b>

> <i>The most advanced Telegram Session Suite for Pyrogram & Telethon accounts.</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <b>String Generator:</b> Pyrogram v2 & Telethon
📱 <b>Device Manager:</b> View Active IPs & Terminate
💼 <b>Account Vault:</b> Encrypted Session Storage
🛡️ <b>Health Checker:</b> Check Alive / Banned Status
🛠 <b>Utility Tools:</b> Leave Channels, Clean Dialogs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 <i>100% Client-side Encrypted & Highly Secure.</i>
"""

HELP_TEXT = """
📖 <b>𝗛𝗢𝗪 𝗧𝗢 𝗨𝗦𝗘 𝗧𝗛𝗜𝗦 𝗕𝗢𝗧</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣ <b>Generate String Session:</b>
• Click on <code>⚡ Generate Session</code>.
• Select Pyrogram v2 or Telethon.
• Use default API or enter your own API_ID & API_HASH.
• Enter your phone number with country code (e.g. <code>+919876543210</code>).
• Enter the OTP code. 
  <i>Tip: If Telegram blocks OTP delivery, enter code with spaces like <code>1 2 3 4 5</code>.</i>
• If 2FA is enabled, enter your password.
• Your session will be sent directly to your <b>Saved Messages</b> for safety!

2️⃣ <b>Active Devices & Security:</b>
• View all logged-in devices, active IPs, countries, and login dates.
• Click <b>Terminate All Other Sessions</b> to kick out all unknown devices immediately.

3️⃣ <b>Account Vault:</b>
• Store your multiple sessions safely with AES-Fernet encryption.
• Run 1-click Alive/Dead status checks on your accounts.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

@Client.on_message(filters.command(["start", "help"]) & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    await db.add_user(user.id, user.first_name, user.username)
    
    if message.text.startswith("/help"):
        await message.reply_text(
            HELP_TEXT,
            reply_markup=back_to_main_keyboard(),
            disable_web_page_preview=True
        )
        return

    await message.reply_text(
        START_TEXT.format(name=user.first_name),
        reply_markup=main_menu_keyboard(config.OWNER_ID, user.id),
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex("^back_main$"))
async def back_main_callback(client: Client, query: CallbackQuery):
    cancel_input(query.from_user.id)
    await query.message.edit_text(
        START_TEXT.format(name=query.from_user.first_name),
        reply_markup=main_menu_keyboard(config.OWNER_ID, query.from_user.id),
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex("^menu_help$"))
async def help_callback(client: Client, query: CallbackQuery):
    await query.message.edit_text(
        HELP_TEXT,
        reply_markup=back_to_main_keyboard(),
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex("^cancel_action$"))
async def cancel_callback(client: Client, query: CallbackQuery):
    cancel_input(query.from_user.id)
    await query.answer("Current operation cancelled ❌", show_alert=False)
    await query.message.edit_text(
        START_TEXT.format(name=query.from_user.first_name),
        reply_markup=main_menu_keyboard(config.OWNER_ID, query.from_user.id),
        disable_web_page_preview=True
    )
