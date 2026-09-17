from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from pyrogram import Client as PyroClient
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
    save_to_vault_keyboard, back_to_main_keyboard, fingerprints_selector_keyboard
)
from helpers.session_tools import DEVICE_FINGERPRINTS
from helpers.states import GenerateStates
from handlers.common import (
    ACTIVE_LOGINS, RECENT_SESSIONS, cleanup_user_login
)

router = Router()

@router.callback_query(F.data == "menu_generate")
async def cb_menu_generate(query: CallbackQuery, state: FSMContext):
    await state.clear()
    text = """
╭━━━━━━━━━━━━━━━━━━━━╮
│  ⚡ <b>ɢᴇɴᴇʀᴀᴛᴇ sᴇssɪᴏɴ sᴛʀɪɴɢ</b>  │
╰━━━━━━━━━━━━━━━━━━━━╯
Kripya select karein aapko kis library ka String Session generate karna hai:

🔹 <b>Pyrogram (v2):</b> Modern bots, userbots, and automation ke liye.
🔹 <b>Telethon:</b> Official MTProto features and stable tools ke liye.
"""
    await query.message.edit_text(text, reply_markup=session_type_keyboard())

@router.callback_query(F.data.in_(["gen_pyrogram", "gen_telethon"]))
async def cb_choose_lib(query: CallbackQuery, state: FSMContext):
    session_type = "pyrogram" if query.data == "gen_pyrogram" else "telethon"
    await state.update_data(session_type=session_type)
    data = await state.get_data()
    fp_key = data.get("fp_key")

    if fp_key:
        fp = DEVICE_FINGERPRINTS.get(fp_key, DEVICE_FINGERPRINTS["default"])
        text = f"""
╭━━━━━━━━━━━━━━━━━━━━╮
│  ⚙️ <b>ᴄʜᴏᴏsᴇ ᴀᴘɪ ᴄʀᴇᴅᴇɴᴛɪᴀʟs</b>  │
╰━━━━━━━━━━━━━━━━━━━━╯
Target Library: <b>{session_type.upper()}</b>
Hardware Profile: <b>{fp['icon']} {fp['name']}</b>

Aap Default Official API use karna chahte hain ya apna khud ka <code>API_ID</code> aur <code>API_HASH</code>?
"""
        await query.message.edit_text(text, reply_markup=api_choice_keyboard(session_type))
    else:
        text = f"""
╭━━━━━━━━━━━━━━━━━━━━╮
│  📱 <b>ᴄʜᴏᴏsᴇ ᴅᴇᴠɪᴄᴇ ғɪɴɢᴇʀᴘʀɪɴᴛ</b>  │
╰━━━━━━━━━━━━━━━━━━━━╯
Target Library: <b>{session_type.upper()}</b>

Session ko real physical device ke roop me disguise karne ke liye Hardware Profile select karein:
"""
        await query.message.edit_text(text, reply_markup=fingerprints_selector_keyboard("gen"))

@router.callback_query(F.data.startswith("fpgen_"))
async def cb_fpgen(query: CallbackQuery, state: FSMContext):
    fp_key = query.data.split("_")[1]
    await state.update_data(fp_key=fp_key)
    data = await state.get_data()
    fp = DEVICE_FINGERPRINTS.get(fp_key, DEVICE_FINGERPRINTS["default"])
    session_type = data.get("session_type")

    if session_type:
        text = f"""
╭━━━━━━━━━━━━━━━━━━━━╮
│  ⚙️ <b>ᴄʜᴏᴏsᴇ ᴀᴘɪ ᴄʀᴇᴅᴇɴᴛɪᴀʟs</b>  │
╰━━━━━━━━━━━━━━━━━━━━╯
Target Library: <b>{session_type.upper()}</b>
Hardware Profile: <b>{fp['icon']} {fp['name']}</b>

Aap Default Official API use karna chahte hain ya apna khud ka <code>API_ID</code> aur <code>API_HASH</code>?
"""
        await query.message.edit_text(text, reply_markup=api_choice_keyboard(session_type))
    else:
        text = f"""
╭━━━━━━━━━━━━━━━━━━━━╮
│  ⚡ <b>ᴄʜᴏᴏsᴇ sᴇssɪᴏɴ ʟɪʙʀᴀʀʏ</b>  │
╰━━━━━━━━━━━━━━━━━━━━╯
Selected Profile: <b>{fp['icon']} {fp['name']}</b>

Kripya select karein aapko kis library ka String Session generate karna hai:

🔹 <b>Pyrogram (v2):</b> Modern bots & high-speed automation.
🔹 <b>Telethon:</b> Official MTProto features & stable tools.
"""
        await query.message.edit_text(text, reply_markup=session_type_keyboard())


@router.callback_query(F.data.startswith("apichoice_"))
async def cb_api_choice(query: CallbackQuery, state: FSMContext):
    parts = query.data.split("_")
    mode = parts[1]
    session_type = parts[2]
    await state.update_data(session_type=session_type)

    if mode == "custom":
        await state.set_state(GenerateStates.waiting_custom_api_id)
        await query.message.edit_text(
            "📝 <b>Enter your API_ID:</b>\n\n(Send /cancel to abort)",
            reply_markup=cancel_keyboard()
        )
    else:
        await state.update_data(api_id=config.API_ID, api_hash=config.API_HASH)
        await state.set_state(GenerateStates.waiting_phone)
        await query.message.edit_text(
            "📞 <b>Enter your Phone Number:</b>\n\n"
            "Include country code (e.g. <code>+919876543210</code>)\n\n"
            "<i>Send /cancel to abort.</i>",
            reply_markup=cancel_keyboard()
        )

@router.message(GenerateStates.waiting_custom_api_id)
async def process_api_id(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return
    if not message.text.strip().isdigit():
        await message.reply("❌ Invalid API_ID! Must be digits only.", reply_markup=cancel_keyboard())
        return
    await state.update_data(api_id=int(message.text.strip()))
    await state.set_state(GenerateStates.waiting_custom_api_hash)
    await message.reply("📝 <b>Now enter your API_HASH:</b>\n\n(Send /cancel to abort)", reply_markup=cancel_keyboard())

@router.message(GenerateStates.waiting_custom_api_hash)
async def process_api_hash(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return
    api_hash = message.text.strip()
    if len(api_hash) < 10:
        await message.reply("❌ Invalid API_HASH.", reply_markup=cancel_keyboard())
        return
    await state.update_data(api_hash=api_hash)
    await state.set_state(GenerateStates.waiting_phone)
    await message.reply(
        "📞 <b>Enter your Phone Number:</b>\n\n"
        "Include country code (e.g. <code>+919876543210</code>)\n\n"
        "<i>Send /cancel to abort.</i>",
        reply_markup=cancel_keyboard()
    )

@router.message(GenerateStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    phone = message.text.strip().replace(" ", "").replace("-", "")
    data = await state.get_data()
    session_type = data["session_type"]
    fp_key = data.get("fp_key", "default")
    fp = DEVICE_FINGERPRINTS.get(fp_key, DEVICE_FINGERPRINTS["default"])
    api_id = data.get("api_id", config.API_ID)
    api_hash = data.get("api_hash", config.API_HASH)
    user_id = message.from_user.id

    status_msg = await message.reply("🔄 <i>Sending login code to Telegram...</i>")

    if session_type == "pyrogram":
        client = PyroClient(
            f"pyr_{user_id}",
            api_id=api_id,
            api_hash=api_hash,
            device_model=fp["device_model"],
            system_version=fp["system_version"],
            app_version=fp["app_version"],
            lang_code=fp["lang_code"],
            in_memory=True
        )
        try:
            await client.connect()
            sent_code = await client.send_code(phone)
            ACTIVE_LOGINS[user_id] = {
                "client": client,
                "phone": phone,
                "phone_code_hash": sent_code.phone_code_hash,
                "type": "pyrogram",
                "fp": fp
            }
        except PhoneNumberInvalid:
            await status_msg.edit_text("❌ Invalid Phone Number! Please check and try again.", reply_markup=back_to_main_keyboard())
            if client.is_connected:
                await client.disconnect()
            await state.clear()
            return
        except FloodWait as e:
            await status_msg.edit_text(f"⏳ FloodWait: Please wait {e.value} seconds.", reply_markup=back_to_main_keyboard())
            if client.is_connected:
                await client.disconnect()
            await state.clear()
            return
        except Exception as e:
            await status_msg.edit_text(f"❌ Error sending code: <code>{e}</code>", reply_markup=back_to_main_keyboard())
            if client.is_connected:
                await client.disconnect()
            await state.clear()
            return
    else:
        client = TelegramClient(
            StringSession(),
            api_id,
            api_hash,
            device_model=fp["device_model"],
            system_version=fp["system_version"],
            app_version=fp["app_version"],
            lang_code=fp["lang_code"],
            system_lang_code=fp["system_lang_code"]
        )
        try:
            await client.connect()
            sent_code = await client.send_code_request(phone)
            ACTIVE_LOGINS[user_id] = {
                "client": client,
                "phone": phone,
                "phone_code_hash": sent_code.phone_code_hash,
                "type": "telethon",
                "fp": fp
            }
        except PhoneNumberInvalidError:
            await status_msg.edit_text("❌ Invalid Phone Number! Please check and try again.", reply_markup=back_to_main_keyboard())
            if client.is_connected():
                await client.disconnect()
            await state.clear()
            return
        except Exception as e:
            await status_msg.edit_text(f"❌ Error sending code: <code>{e}</code>", reply_markup=back_to_main_keyboard())
            if client.is_connected():
                await client.disconnect()
            await state.clear()
            return

    await state.set_state(GenerateStates.waiting_otp)
    await status_msg.edit_text(
        "📩 <b>OTP sent to your Telegram Account!</b>\n\n"
        "Kripya code enter karein.\n"
        "💡 <b>Important:</b> Agar Telegram OTP accept na kare, to spaces ke sath bhejein (e.g. <code>1 2 3 4 5</code>).\n\n"
        "<i>Send /cancel to abort.</i>",
        reply_markup=cancel_keyboard()
    )

@router.message(GenerateStates.waiting_otp)
async def process_otp(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await cleanup_user_login(message.from_user.id)
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    user_id = message.from_user.id
    if user_id not in ACTIVE_LOGINS:
        await message.reply("Session expired. Please start again from /start", reply_markup=back_to_main_keyboard())
        await state.clear()
        return

    otp = message.text.replace(" ", "").replace("-", "").strip()
    try:
        await message.delete()
    except Exception:
        pass

    status_msg = await message.answer("🔄 <i>Verifying OTP...</i>")
    login = ACTIVE_LOGINS[user_id]
    client = login["client"]
    phone = login["phone"]
    code_hash = login["phone_code_hash"]
    session_type = login["type"]

    if session_type == "pyrogram":
        try:
            await client.sign_in(phone, code_hash, otp)
        except SessionPasswordNeeded:
            await state.set_state(GenerateStates.waiting_2fa)
            await status_msg.edit_text(
                "🔐 <b>Two-Step Verification (2FA) is Enabled!</b>\n\n"
                "Kripya apna 2FA Password enter karein:\n\n"
                "<i>(Aapka password secure rahega aur turant chat se delete kar diya jayega)</i>",
                reply_markup=cancel_keyboard()
            )
            return
        except (PhoneCodeInvalid, PhoneCodeExpired):
            await status_msg.edit_text("❌ Invalid or Expired OTP! Please try again.", reply_markup=back_to_main_keyboard())
            await cleanup_user_login(user_id)
            await state.clear()
            return
        except Exception as e:
            await status_msg.edit_text(f"❌ Login failed: <code>{e}</code>", reply_markup=back_to_main_keyboard())
            await cleanup_user_login(user_id)
            await state.clear()
            return

        me = await client.get_me()
        string_session = await client.export_session_string()
        try:
            await client.send_message("me", f"❄️ <b>ICE BOT SESSION GENERATED</b> ❄️\n\n<code>{string_session}</code>\n\n⚠️ Keep this session string completely confidential!")
        except Exception:
            pass
        if client.is_connected:
            await client.disconnect()
    else:
        try:
            await client.sign_in(phone, code=otp, phone_code_hash=code_hash)
        except SessionPasswordNeededError:
            await state.set_state(GenerateStates.waiting_2fa)
            await status_msg.edit_text(
                "🔐 <b>Two-Step Verification (2FA) is Enabled!</b>\n\n"
                "Kripya apna 2FA Password enter karein:\n\n"
                "<i>(Aapka password secure rahega aur turant chat se delete kar diya jayega)</i>",
                reply_markup=cancel_keyboard()
            )
            return
        except (PhoneCodeInvalidError, PhoneCodeExpiredError):
            await status_msg.edit_text("❌ Invalid or Expired OTP! Please try again.", reply_markup=back_to_main_keyboard())
            await cleanup_user_login(user_id)
            await state.clear()
            return
        except Exception as e:
            await status_msg.edit_text(f"❌ Login failed: <code>{e}</code>", reply_markup=back_to_main_keyboard())
            await cleanup_user_login(user_id)
            await state.clear()
            return

        me = await client.get_me()
        string_session = client.session.save()
        try:
            await client.send_message("me", f"❄️ **ICE BOT SESSION GENERATED** ❄️\n\n`{string_session}`\n\n⚠️ Keep this session string completely confidential!")
        except Exception:
            pass
        if client.is_connected():
            await client.disconnect()

    login_info = ACTIVE_LOGINS.pop(user_id, {})
    await state.clear()

    fp_info = login_info.get("fp", DEVICE_FINGERPRINTS["default"])
    dev_name = f"{fp_info.get('icon', '📱')} {fp_info.get('name', 'Official App')}"

    RECENT_SESSIONS[user_id] = {
        "type": session_type,
        "session": string_session,
        "phone": phone,
        "name": me.first_name,
        "tg_user_id": me.id,
        "device": fp_info.get("name", "Official App")
    }

    success_text = f"""
✨ <b>{session_type.upper()} SESSION GENERATED!</b> ✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Account:</b> {me.first_name}
🆔 <b>User ID:</b> <code>{me.id}</code>
📞 <b>Phone:</b> <code>{phone}</code>
📱 <b>Device:</b> <code>{dev_name}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<code>{string_session}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>Warning:</b> Never share this string session with anyone!
"""
    await status_msg.edit_text(success_text, reply_markup=save_to_vault_keyboard(session_type))

@router.message(GenerateStates.waiting_2fa)
async def process_2fa(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await cleanup_user_login(message.from_user.id)
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    user_id = message.from_user.id
    if user_id not in ACTIVE_LOGINS:
        await message.reply("Session expired. Please start again from /start", reply_markup=back_to_main_keyboard())
        await state.clear()
        return

    password = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass

    status_msg = await message.answer("🔄 <i>Verifying 2FA Password...</i>")
    login = ACTIVE_LOGINS[user_id]
    client = login["client"]
    phone = login["phone"]
    session_type = login["type"]

    if session_type == "pyrogram":
        try:
            await client.check_password(password)
        except PasswordHashInvalid:
            await status_msg.edit_text("❌ Incorrect 2FA Password! Please try again.", reply_markup=back_to_main_keyboard())
            await cleanup_user_login(user_id)
            await state.clear()
            return
        except Exception as e:
            await status_msg.edit_text(f"❌ 2FA verification failed: <code>{e}</code>", reply_markup=back_to_main_keyboard())
            await cleanup_user_login(user_id)
            await state.clear()
            return

        me = await client.get_me()
        string_session = await client.export_session_string()
        try:
            await client.send_message("me", f"❄️ <b>ICE BOT SESSION GENERATED</b> ❄️\n\n<code>{string_session}</code>\n\n⚠️ Keep this session string completely confidential!")
        except Exception:
            pass
        if client.is_connected:
            await client.disconnect()
    else:
        try:
            await client.sign_in(password=password)
        except PasswordHashInvalidError:
            await status_msg.edit_text("❌ Incorrect 2FA Password! Please try again.", reply_markup=back_to_main_keyboard())
            await cleanup_user_login(user_id)
            await state.clear()
            return
        except Exception as e:
            await status_msg.edit_text(f"❌ 2FA verification failed: <code>{e}</code>", reply_markup=back_to_main_keyboard())
            await cleanup_user_login(user_id)
            await state.clear()
            return

        me = await client.get_me()
        string_session = client.session.save()
        try:
            await client.send_message("me", f"❄️ **ICE BOT SESSION GENERATED** ❄️\n\n`{string_session}`\n\n⚠️ Keep this session string completely confidential!")
        except Exception:
            pass
        if client.is_connected():
            await client.disconnect()

    login_info = ACTIVE_LOGINS.pop(user_id, {})
    await state.clear()

    fp_info = login_info.get("fp", DEVICE_FINGERPRINTS["default"])
    dev_name = f"{fp_info.get('icon', '📱')} {fp_info.get('name', 'Official App')}"

    RECENT_SESSIONS[user_id] = {
        "type": session_type,
        "session": string_session,
        "phone": phone,
        "name": me.first_name,
        "tg_user_id": me.id,
        "device": fp_info.get("name", "Official App")
    }

    success_text = f"""
✨ <b>{session_type.upper()} SESSION GENERATED!</b> ✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Account:</b> {me.first_name}
🆔 <b>User ID:</b> <code>{me.id}</code>
📞 <b>Phone:</b> <code>{phone}</code>
📱 <b>Device:</b> <code>{dev_name}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<code>{string_session}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>Warning:</b> Never share this string session with anyone!
"""
    await status_msg.edit_text(success_text, reply_markup=save_to_vault_keyboard(session_type))

@router.callback_query(F.data.startswith("vault_save_recent_"))
async def cb_save_recent_vault(query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in RECENT_SESSIONS:
        await query.answer("Session expired from cache. Please add it from Vault menu!", show_alert=True)
        return

    data = RECENT_SESSIONS[user_id]
    dev_suffix = f" ({data.get('device', 'Device')})" if data.get('device') else ""
    await db.save_account(
        user_id=user_id,
        session_type=data["type"],
        account_name=f"{data['name']}{dev_suffix}",
        phone=data["phone"],
        tg_user_id=data["tg_user_id"],
        raw_session=data["session"]
    )
    await query.answer("Saved securely to Account Vault! 💼", show_alert=True)
    await query.message.reply("💼 Session is now saved in your encrypted Vault.", reply_markup=back_to_main_keyboard())
