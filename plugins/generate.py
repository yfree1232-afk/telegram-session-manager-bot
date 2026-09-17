import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    SessionPasswordNeeded, FloodWait, PhoneNumberInvalid,
    PhoneCodeInvalid, PhoneCodeExpired, PasswordHashInvalid
)
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, PhoneNumberInvalidError,
    PhoneCodeInvalidError, PhoneCodeExpiredError, PasswordHashInvalidError
)

import config
from database.db import db
from helpers.keyboard import (
    session_type_keyboard, api_choice_keyboard, cancel_keyboard,
    save_to_vault_keyboard, back_to_main_keyboard
)
from helpers.listener import wait_for_input, cancel_input, LISTENERS

# Temp storage for recently generated sessions: user_id -> {"type": ..., "session": ..., "phone": ..., "name": ...}
RECENT_SESSIONS = {}

@Client.on_message(filters.private & ~filters.command(["start", "help"]), group=1)
async def listener_interceptor(client: Client, message: Message):
    """Intercept messages if there is a pending listener for this user."""
    chat_id = message.chat.id
    if chat_id in LISTENERS:
        fut = LISTENERS[chat_id]
        if not fut.done():
            if message.text and message.text.strip().lower() == "/cancel":
                cancel_input(chat_id)
                await message.reply_text("❌ Operation cancelled.", reply_markup=back_to_main_keyboard())
                return
            fut.set_result(message)

@Client.on_callback_query(filters.regex("^menu_generate$"))
async def generate_menu_callback(client: Client, query: CallbackQuery):
    cancel_input(query.from_user.id)
    text = """
╭━━━━━━━━━━━━━━━━━━━━╮
│  ⚡ <b>ɢᴇɴᴇʀᴀᴛᴇ sᴇssɪᴏɴ sᴛʀɪɴɢ</b>  │
╰━━━━━━━━━━━━━━━━━━━━╯
Kripya select karein aapko kis library ka String Session generate karna hai:

🔹 <b>Pyrogram (v2):</b> Modern bots, userbots, and automation ke liye.
🔹 <b>Telethon:</b> Official MTProto features and stable tools ke liye.
"""
    await query.message.edit_text(text, reply_markup=session_type_keyboard())

@Client.on_callback_query(filters.regex("^gen_(pyrogram|telethon)$"))
async def choose_api_mode_callback(client: Client, query: CallbackQuery):
    session_type = query.matches[0].group(1)
    text = f"""
╭━━━━━━━━━━━━━━━━━━━━╮
│  ⚙️ <b>ᴄʜᴏᴏsᴇ ᴀᴘɪ ᴄʀᴇᴅᴇɴᴛɪᴀʟs</b>  │
╰━━━━━━━━━━━━━━━━━━━━╯
Target Library: <b>{session_type.upper()}</b>

Aap Default Telegram Official API use karna chahte hain ya apna khud ka <code>API_ID</code> aur <code>API_HASH</code>?
"""
    await query.message.edit_text(text, reply_markup=api_choice_keyboard(session_type))

@Client.on_callback_query(filters.regex("^apichoice_(default|custom)_(pyrogram|telethon)$"))
async def start_generator_wizard(client: Client, query: CallbackQuery):
    choice = query.matches[0].group(1)
    session_type = query.matches[0].group(2)
    user_id = query.from_user.id

    api_id = config.API_ID
    api_hash = config.API_HASH

    if choice == "custom":
        await query.message.edit_text(
            "📝 <b>Enter your API_ID:</b>\n\n(Send /cancel to abort)",
            reply_markup=cancel_keyboard()
        )
        try:
            msg = await wait_for_input(client, user_id, timeout=120)
            if not msg.text or not msg.text.isdigit():
                await msg.reply_text("❌ Invalid API_ID. It must be numbers only.", reply_markup=back_to_main_keyboard())
                return
            api_id = int(msg.text.strip())
        except (asyncio.TimeoutError, ValueError):
            return

        await query.message.reply_text(
            "📝 <b>Now enter your API_HASH:</b>\n\n(Send /cancel to abort)",
            reply_markup=cancel_keyboard()
        )
        try:
            msg = await wait_for_input(client, user_id, timeout=120)
            if not msg.text or len(msg.text.strip()) < 10:
                await msg.reply_text("❌ Invalid API_HASH.", reply_markup=back_to_main_keyboard())
                return
            api_hash = msg.text.strip()
        except (asyncio.TimeoutError, ValueError):
            return

    # Ask Phone Number
    await query.message.reply_text(
        "📞 <b>Enter your Phone Number:</b>\n\n"
        "Include country code (e.g. <code>+919876543210</code> or <code>+14155552671</code>)\n\n"
        "<i>Send /cancel to abort.</i>",
        reply_markup=cancel_keyboard()
    )

    try:
        phone_msg = await wait_for_input(client, user_id, timeout=120)
        phone = phone_msg.text.strip().replace(" ", "").replace("-", "")
    except (asyncio.TimeoutError, ValueError):
        return

    # Process Session Generation
    status_msg = await phone_msg.reply_text("🔄 <i>Sending login code to Telegram...</i>")

    if session_type == "pyrogram":
        await _generate_pyrogram(client, user_id, status_msg, phone, api_id, api_hash)
    else:
        await _generate_telethon(client, user_id, status_msg, phone, api_id, api_hash)

async def _generate_pyrogram(client: Client, user_id: int, status_msg: Message, phone: str, api_id: int, api_hash: str):
    temp_client = Client(
        name=f"pyr_{user_id}",
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True
    )
    try:
        await temp_client.connect()
    except Exception as e:
        await status_msg.edit_text(f"❌ Failed to connect: <code>{e}</code>", reply_markup=back_to_main_keyboard())
        return

    try:
        sent_code = await temp_client.send_code(phone)
    except PhoneNumberInvalid:
        await status_msg.edit_text("❌ Invalid Phone Number! Please check and try again.", reply_markup=back_to_main_keyboard())
        await temp_client.disconnect()
        return
    except FloodWait as e:
        await status_msg.edit_text(f"⏳ FloodWait: Please wait {e.value} seconds.", reply_markup=back_to_main_keyboard())
        await temp_client.disconnect()
        return
    except Exception as e:
        await status_msg.edit_text(f"❌ Error sending code: <code>{e}</code>", reply_markup=back_to_main_keyboard())
        await temp_client.disconnect()
        return

    await status_msg.edit_text(
        "📩 <b>OTP sent to your Telegram Account!</b>\n\n"
        "Kripya code enter karein.\n"
        "💡 <b>Important:</b> Agar Telegram OTP accept na kare, to spaces ke sath bhejein (e.g. <code>1 2 3 4 5</code>).\n\n"
        "<i>Send /cancel to abort.</i>",
        reply_markup=cancel_keyboard()
    )

    try:
        otp_msg = await wait_for_input(client, user_id, timeout=180)
        otp = otp_msg.text.replace(" ", "").replace("-", "").strip()
        try:
            await otp_msg.delete()
        except Exception:
            pass
    except (asyncio.TimeoutError, ValueError):
        await temp_client.disconnect()
        return

    try:
        await temp_client.sign_in(phone, sent_code.phone_code_hash, otp)
    except SessionPasswordNeeded:
        await status_msg.edit_text(
            "🔐 <b>Two-Step Verification (2FA) is Enabled!</b>\n\n"
            "Kripya apna 2FA Password enter karein:\n\n"
            "<i>(Aapka password secure rahega aur check hote hi delete kar diya jayega)</i>",
            reply_markup=cancel_keyboard()
        )
        try:
            pwd_msg = await wait_for_input(client, user_id, timeout=180)
            password = pwd_msg.text.strip()
            try:
                await pwd_msg.delete()
            except Exception:
                pass
            await temp_client.check_password(password)
        except (asyncio.TimeoutError, ValueError):
            await temp_client.disconnect()
            return
        except PasswordHashInvalid:
            await status_msg.edit_text("❌ Incorrect 2FA Password! Please try again.", reply_markup=back_to_main_keyboard())
            await temp_client.disconnect()
            return
    except (PhoneCodeInvalid, PhoneCodeExpired):
        await status_msg.edit_text("❌ Invalid or Expired OTP! Please try again.", reply_markup=back_to_main_keyboard())
        await temp_client.disconnect()
        return
    except Exception as e:
        await status_msg.edit_text(f"❌ Login failed: <code>{e}</code>", reply_markup=back_to_main_keyboard())
        await temp_client.disconnect()
        return

    me = await temp_client.get_me()
    string_session = await temp_client.export_session_string()
    await temp_client.disconnect()

    RECENT_SESSIONS[user_id] = {
        "type": "pyrogram",
        "session": string_session,
        "phone": phone,
        "name": me.first_name,
        "tg_user_id": me.id
    }

    success_text = f"""
✨ <b>PYROGRAM v2 SESSION GENERATED!</b> ✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Account:</b> {me.first_name}
🆔 <b>User ID:</b> <code>{me.id}</code>
📞 <b>Phone:</b> <code>{phone}</code>
🌐 <b>DC:</b> {me.dc_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<code>{string_session}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>Warning:</b> Never share this string session with anyone!
"""
    await status_msg.edit_text(success_text, reply_markup=save_to_vault_keyboard("pyrogram"))

async def _generate_telethon(client: Client, user_id: int, status_msg: Message, phone: str, api_id: int, api_hash: str):
    temp_client = TelegramClient(StringSession(), api_id, api_hash)
    try:
        await temp_client.connect()
    except Exception as e:
        await status_msg.edit_text(f"❌ Failed to connect: <code>{e}</code>", reply_markup=back_to_main_keyboard())
        return

    try:
        sent_code = await temp_client.send_code_request(phone)
    except PhoneNumberInvalidError:
        await status_msg.edit_text("❌ Invalid Phone Number! Please check and try again.", reply_markup=back_to_main_keyboard())
        await temp_client.disconnect()
        return
    except Exception as e:
        await status_msg.edit_text(f"❌ Error sending code: <code>{e}</code>", reply_markup=back_to_main_keyboard())
        await temp_client.disconnect()
        return

    await status_msg.edit_text(
        "📩 <b>OTP sent to your Telegram Account!</b>\n\n"
        "Kripya code enter karein.\n"
        "💡 <b>Important:</b> Agar Telegram OTP accept na kare, to spaces ke sath bhejein (e.g. <code>1 2 3 4 5</code>).\n\n"
        "<i>Send /cancel to abort.</i>",
        reply_markup=cancel_keyboard()
    )

    try:
        otp_msg = await wait_for_input(client, user_id, timeout=180)
        otp = otp_msg.text.replace(" ", "").replace("-", "").strip()
        try:
            await otp_msg.delete()
        except Exception:
            pass
    except (asyncio.TimeoutError, ValueError):
        await temp_client.disconnect()
        return

    try:
        await temp_client.sign_in(phone, code=otp, phone_code_hash=sent_code.phone_code_hash)
    except SessionPasswordNeededError:
        await status_msg.edit_text(
            "🔐 <b>Two-Step Verification (2FA) is Enabled!</b>\n\n"
            "Kripya apna 2FA Password enter karein:\n\n"
            "<i>(Aapka password secure rahega aur check hote hi delete kar diya jayega)</i>",
            reply_markup=cancel_keyboard()
        )
        try:
            pwd_msg = await wait_for_input(client, user_id, timeout=180)
            password = pwd_msg.text.strip()
            try:
                await pwd_msg.delete()
            except Exception:
                pass
            await temp_client.sign_in(password=password)
        except (asyncio.TimeoutError, ValueError):
            await temp_client.disconnect()
            return
        except PasswordHashInvalidError:
            await status_msg.edit_text("❌ Incorrect 2FA Password! Please try again.", reply_markup=back_to_main_keyboard())
            await temp_client.disconnect()
            return
    except (PhoneCodeInvalidError, PhoneCodeExpiredError):
        await status_msg.edit_text("❌ Invalid or Expired OTP! Please try again.", reply_markup=back_to_main_keyboard())
        await temp_client.disconnect()
        return
    except Exception as e:
        await status_msg.edit_text(f"❌ Login failed: <code>{e}</code>", reply_markup=back_to_main_keyboard())
        await temp_client.disconnect()
        return

    me = await temp_client.get_me()
    string_session = temp_client.session.save()
    await temp_client.disconnect()

    RECENT_SESSIONS[user_id] = {
        "type": "telethon",
        "session": string_session,
        "phone": phone,
        "name": me.first_name,
        "tg_user_id": me.id
    }

    success_text = f"""
✨ <b>TELETHON SESSION GENERATED!</b> ✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Account:</b> {me.first_name}
🆔 <b>User ID:</b> <code>{me.id}</code>
📞 <b>Phone:</b> <code>{phone}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<code>{string_session}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>Warning:</b> Never share this string session with anyone!
"""
    await status_msg.edit_text(success_text, reply_markup=save_to_vault_keyboard("telethon"))

@Client.on_callback_query(filters.regex("^vault_save_recent_(pyrogram|telethon)$"))
async def save_recent_to_vault(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in RECENT_SESSIONS:
        await query.answer("Session expired from cache. Please add it from Vault menu!", show_alert=True)
        return

    data = RECENT_SESSIONS[user_id]
    await db.save_account(
        user_id=user_id,
        session_type=data["type"],
        account_name=data["name"] or "Telegram Account",
        phone=data["phone"],
        tg_user_id=data["tg_user_id"],
        raw_session=data["session"]
    )
    await query.answer("✅ Saved securely to your Account Vault!", show_alert=True)
    await query.message.reply_text("💼 Session is now saved in your encrypted Vault.", reply_markup=back_to_main_keyboard())
