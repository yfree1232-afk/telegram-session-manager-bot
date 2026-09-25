import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import io
import qrcode
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
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
    save_to_vault_keyboard, back_to_main_keyboard, fingerprints_selector_keyboard,
    session_phone_prompt_keyboard
)
from helpers.session_tools import DEVICE_FINGERPRINTS, to_pyrogram_session, to_telethon_session
from helpers.states import GenerateStates
from handlers.common import (
    ACTIVE_LOGINS, RECENT_SESSIONS, cleanup_user_login
)

router = Router()

@router.callback_query(F.data == "menu_generate")
async def cb_menu_generate(query: CallbackQuery, state: FSMContext):
    await state.clear()
    text = """
<tg-emoji emoji-id="5445284980978621387">⚡</tg-emoji> <b>ɢᴇɴᴇʀᴀᴛᴇ sᴇssɪᴏɴ sᴛʀɪɴɢ</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Apne account ka session generate karne ke tareeqe:

<tg-emoji emoji-id="5931718859366075705">✨</tg-emoji> <b>1. ǫʀ ᴄᴏᴅᴇ ʟᴏɢɪɴ (ʀᴇᴄᴏᴍᴍᴇɴᴅᴇᴅ - ɴᴏ ᴏᴛᴘ!):</b>
• <b>Zero OTP wait:</b> Instant 1-second login!
• Telegram App ➔ <b>Settings > Devices > Link Desktop Device</b> se scan karein.

<tg-emoji emoji-id="5409230963911701228">📩</tg-emoji> <b>2. ᴘʏʀᴏɢʀᴀᴍ / ᴛᴇʟᴇᴛʜᴏɴ (ᴘʜᴏɴᴇ ᴏᴛᴘ):</b>
• Phone number enter karke official Telegram App (Chat 777000) me OTP mangwayein.
""".strip()
    try:
        await query.message.edit_text(text, reply_markup=session_type_keyboard())
    except Exception:
        await query.message.answer(text, reply_markup=session_type_keyboard())

@router.callback_query(F.data == "gen_qr")
async def cb_gen_qr(query: CallbackQuery, state: FSMContext):
    await state.clear()
    status_msg = await query.message.answer("🔄 <i>Generating official Telegram QR Code... Please wait.</i>")
    client = TelegramClient(
        StringSession(),
        config.API_ID,
        config.API_HASH,
        device_model="Telegram Desktop",
        system_version="Windows 11 x64",
        app_version="5.2.2 x64",
        lang_code="en",
        system_lang_code="en-US"
    )
    try:
        await client.connect()
        qr_login = await client.qr_login()

        qr_img = qrcode.make(qr_login.url)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)

        photo = BufferedInputFile(buf.getvalue(), filename="telegram_qr_login.png")
        try:
            await status_msg.delete()
        except Exception:
            pass

        qr_msg = await query.message.answer_photo(
            photo,
            caption=(
                "<tg-emoji emoji-id=\"5445284980978621387\">⚡</tg-emoji> <b>SCAN QR CODE TO LOGIN (INSTANT)</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "1. Apne mobile me official <b>Telegram App</b> open karein.\n"
                "2. <b>Settings > Devices > Link Desktop Device</b> par click karein.\n"
                "3. Apna camera is QR Code par point karke scan karein!\n\n"
                "<tg-emoji emoji-id=\"5931718859366075705\">✨</tg-emoji> <b>Koi OTP / SMS nahi lagega! Session turant generate ho jayega.</b>\n"
                "⏳ <i>Valid for 60 seconds... Waiting for scan.</i>"
            ),
            reply_markup=cancel_keyboard()
        )

        try:
            user = await qr_login.wait(timeout=60)
            session_str = client.session.save()
            pyro_str = to_pyrogram_session(session_str)

            user_id = query.from_user.id
            account_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Telegram User"
            await db.save_account(
                user_id=user_id,
                session_type="telethon",
                account_name=account_name,
                phone=user.phone or "QR_Linked",
                tg_user_id=user.id,
                raw_session=session_str
            )

            success_text = f"""
🎉 <b>TELEGRAM SESSION GENERATED SUCCESSFULLY!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>User:</b> {account_name}
🆔 <b>User ID:</b> <code>{user.id}</code>
📞 <b>Phone:</b> <code>{user.phone or 'N/A'}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔹 <b>Telethon Session:</b>
<code>{session_str}</code>

🔹 <b>Pyrogram (v2) Session:</b>
<code>{pyro_str}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💾 <i>Session aapke Vault me save ho gaya hai aur Saved Messages me bhi bhej diya gaya hai!</i>
""".strip()
            await qr_msg.reply(success_text, reply_markup=back_to_main_keyboard())
            try:
                await client.send_message("me", f"⚡ <b>New Session Generated via ICE Bot:</b>\n\nTelethon:\n<code>{session_str}</code>\n\nPyrogram:\n<code>{pyro_str}</code>")
            except Exception:
                pass
        except asyncio.TimeoutError:
            await qr_msg.reply("⏳ <i>QR Code expired. Dubara try karne ke liye /generate dabayein.</i>", reply_markup=back_to_main_keyboard())
        except SessionPasswordNeededError:
            ACTIVE_LOGINS[query.from_user.id] = {
                "client": client,
                "phone": "QR_User",
                "phone_code_hash": "",
                "type": "telethon",
                "fp": DEVICE_FINGERPRINTS["default"],
                "attempts": 0
            }
            await state.set_state(GenerateStates.waiting_password)
            await qr_msg.reply(
                "🔐 <b>2FA Password Required!</b>\n\n"
                "Aapke account par Two-Step Verification enabled hai.\n"
                "Kripya apna 2FA password yahan message me bhejein:",
                reply_markup=cancel_keyboard()
            )
            return
        except Exception as e:
            await qr_msg.reply(f"❌ Error during QR login: <code>{e}</code>", reply_markup=back_to_main_keyboard())
    except Exception as e:
        await query.message.answer(f"❌ Failed to initialize QR login: <code>{e}</code>", reply_markup=back_to_main_keyboard())
    finally:
        current_state = await state.get_state()
        if current_state != GenerateStates.waiting_password.state and client.is_connected():
            await client.disconnect()

@router.callback_query(F.data.in_(["gen_pyrogram", "gen_telethon"]))
async def cb_choose_lib(query: CallbackQuery, state: FSMContext):
    session_type = "pyrogram" if query.data == "gen_pyrogram" else "telethon"
    fp = DEVICE_FINGERPRINTS["default"]
    await state.update_data(
        session_type=session_type,
        fp_key="default",
        api_id=fp.get("api_id", config.API_ID),
        api_hash=fp.get("api_hash", config.API_HASH)
    )
    await state.set_state(GenerateStates.waiting_phone)
    text = f"""
⚡ <b>{session_type.upper()} SESSION GENERATION</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📞 <b>Kripya apna Phone Number enter karein:</b>

💡 <i>Country code ke sath enter karein:</i>
Example: <code>+919876543210</code>

⚠️ <b>Notice:</b> Login OTP aapke <b>Telegram App (Chat ID 777000)</b> me aayega.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await query.message.edit_text(text, reply_markup=session_phone_prompt_keyboard(session_type))

@router.callback_query(F.data.startswith("gen_adv_"))
async def cb_gen_adv(query: CallbackQuery, state: FSMContext):
    session_type = query.data.split("_")[2]
    await state.update_data(session_type=session_type)
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
        data = await state.get_data()
        fp_key = data.get("fp_key", "default")
        fp = DEVICE_FINGERPRINTS.get(fp_key, DEVICE_FINGERPRINTS["default"])
        await state.update_data(api_id=fp.get("api_id", config.API_ID), api_hash=fp.get("api_hash", config.API_HASH))
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
    if not phone.startswith("+"):
        if len(phone) == 10 and phone.isdigit():
            phone = "+91" + phone  # Default to India
        elif phone.isdigit():
            phone = "+" + phone
        else:
            await message.reply(
                "❌ <b>Invalid Phone Number!</b>\n\n"
                "Kripya sahi number country code ke sath enter karein.\n"
                "Example: <code>+919876543210</code>",
                reply_markup=cancel_keyboard()
            )
            return

    if len(phone) < 8 or not phone[1:].isdigit():
        await message.reply(
            "❌ <b>Invalid Phone Number!</b>\n\n"
            "Kripya sahi number country code ke sath enter karein.\n"
            "Example: <code>+919876543210</code>",
            reply_markup=cancel_keyboard()
        )
        return

    data = await state.get_data()
    session_type = data.get("session_type", "pyrogram")
    fp_key = data.get("fp_key", "default")
    fp = DEVICE_FINGERPRINTS.get(fp_key, DEVICE_FINGERPRINTS["default"])
    api_id = data.get("api_id") or fp.get("api_id", config.API_ID)
    api_hash = data.get("api_hash") or fp.get("api_hash", config.API_HASH)
    user_id = message.from_user.id

    status_msg = await message.reply("🔄 <i>Connecting to Telegram & requesting login code...</i>")

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
                "fp": fp,
                "attempts": 0
            }
            code_type_str = str(getattr(sent_code, "type", "")).lower()
        except PhoneNumberInvalid:
            await status_msg.edit_text("❌ Invalid Phone Number! Please check your country code and try again.", reply_markup=back_to_main_keyboard())
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
                "fp": fp,
                "attempts": 0
            }
            code_type_str = type(sent_code.type).__name__.lower()
        except PhoneNumberInvalidError:
            await status_msg.edit_text("❌ Invalid Phone Number! Please check your country code and try again.", reply_markup=back_to_main_keyboard())
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

    if "app" in code_type_str:
        dest_title = "💬 Telegram App (Chat 777000)"
        dest_desc = (
            "⚠️ <b>Dhyan Dein:</b> OTP aapke SIM card par SMS me <b>NAHI</b> gaya hai!\n\n"
            "👉 Ye 5-digit code aapke <b>Telegram App</b> ke andar <b>'Telegram'</b> ke official service notification chat (ID 777000) me aaya hai.\n\n"
            "📱 <i>Kripya apna Telegram app open karein aur sabse upar 'Telegram' chat se 5-digit code dekhein.</i>\n"
            "📲 <i>Agar SIM par SMS chahiye, to neeche 'Resend Code (SMS)' dabayein.</i>"
        )
    elif "sms" in code_type_str:
        dest_title = "📱 Mobile SMS"
        dest_desc = "👉 Code aapke mobile SIM ke SMS inbox me bhej diya gaya hai. SMS inbox check karein."
    elif "call" in code_type_str:
        dest_title = "📞 Automated Phone Call"
        dest_desc = "👉 Telegram aapke number par automated call karke OTP bolega. Call receive karein."
    else:
        dest_title = "💬 Telegram App / SMS"
        dest_desc = "👉 Code Telegram App (chat 777000) ya SMS par bhej diya gaya hai."

    await state.set_state(GenerateStates.waiting_otp)
    otp_text = f"""
📩 <b>LOGIN OTP SENT SUCCESSFULLY!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📞 <b>Target Phone:</b> <code>{phone}</code>
📍 <b>Destination:</b> <b>{dest_title}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{dest_desc}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✍️ <b>5-digit Code yahan enter karein:</b>
💡 <i>Tip: Agar code accept na ho to spaces ke sath bhejein (e.g. <code>1 2 3 4 5</code>).</i>
""".strip()

    otp_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Resend Code (SMS)", callback_data="resend_otp_code")],
        [InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op")]
    ])
    await status_msg.edit_text(otp_text, reply_markup=otp_kb)

@router.callback_query(F.data == "resend_otp_code")
async def cb_resend_otp_code(query: CallbackQuery, state: FSMContext):
    user_id = query.from_user.id
    if user_id not in ACTIVE_LOGINS:
        await query.answer("Session expired. Pehle /start karein!", show_alert=True)
        return

    login = ACTIVE_LOGINS[user_id]
    client = login["client"]
    phone = login["phone"]
    stype = login["type"]

    await query.answer("Requesting SMS resend...", show_alert=False)
    prog = await query.message.reply("🔄 <i>Telegram se SMS ke dwara code dubara mangwaya ja raha hai...</i>")

    try:
        if stype == "pyrogram":
            sent_code = await client.resend_code(phone, login["phone_code_hash"])
            login["phone_code_hash"] = sent_code.phone_code_hash
        else:
            sent_code = await client.send_code_request(phone, force_sms=True)
            login["phone_code_hash"] = sent_code.phone_code_hash

        await prog.delete()
        await query.message.reply(
            f"✅ <b>SMS Requested for {phone}!</b>\n\n"
            f"Apne mobile ka SMS inbox check karein aur 5-digit code enter karein (e.g. <code>1 2 3 4 5</code>).",
            reply_markup=cancel_keyboard()
        )
    except FloodWait as e:
        await prog.edit_text(f"⏳ FloodWait: Please wait {e.value} seconds before resending.")
    except Exception as e:
        await prog.edit_text(f"⚠️ Telegram notice: <code>{e}</code>\n\nAgar SMS na aaye to Telegram app (chat 777000) check karein.")

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
        except PhoneCodeInvalid:
            login["attempts"] = login.get("attempts", 0) + 1
            if login["attempts"] >= 3:
                await status_msg.edit_text("❌ 3 Invalid attempts! Login cancelled.", reply_markup=back_to_main_keyboard())
                await cleanup_user_login(user_id)
                await state.clear()
            else:
                rem = 3 - login["attempts"]
                await status_msg.edit_text(
                    f"❌ <b>Invalid OTP!</b> ({rem} attempts remaining)\n\n"
                    "Kripya sahi 5-digit code dubara enter karein (Spaces ke sath try karein, e.g. <code>1 2 3 4 5</code>):",
                    reply_markup=cancel_keyboard()
                )
            return
        except PhoneCodeExpired:
            await status_msg.edit_text("⏳ OTP Expired! Please click /start to generate a new session.", reply_markup=back_to_main_keyboard())
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
        except PhoneCodeInvalidError:
            login["attempts"] = login.get("attempts", 0) + 1
            if login["attempts"] >= 3:
                await status_msg.edit_text("❌ 3 Invalid attempts! Login cancelled.", reply_markup=back_to_main_keyboard())
                await cleanup_user_login(user_id)
                await state.clear()
            else:
                rem = 3 - login["attempts"]
                await status_msg.edit_text(
                    f"❌ <b>Invalid OTP!</b> ({rem} attempts remaining)\n\n"
                    "Kripya sahi 5-digit code dubara enter karein (Spaces ke sath try karein, e.g. <code>1 2 3 4 5</code>):",
                    reply_markup=cancel_keyboard()
                )
            return
        except PhoneCodeExpiredError:
            await status_msg.edit_text("⏳ OTP Expired! Please click /start to generate a new session.", reply_markup=back_to_main_keyboard())
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
