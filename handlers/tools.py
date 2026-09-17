import io
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile
)
import config
from database.db import db
from helpers.keyboard import (
    tools_menu_keyboard, session_source_keyboard, cancel_keyboard,
    back_to_main_keyboard, fingerprints_selector_keyboard, user_center_keyboard,
    language_keyboard, main_menu_keyboard
)
from helpers.states import ToolStates, DeviceStates
from helpers.session_tools import (
    leave_all_dialogs, check_session_health,
    check_2fa_status, get_account_full_info,
    check_spambot_status, delete_all_dialogs,
    DEVICE_FINGERPRINTS, estimate_account_age,
    check_account_privacy, convert_session,
    read_latest_otp, manage_contacts,
    parse_session_file, extract_all_sessions_from_bytes,
    create_zip_archive
)
from handlers.common import detect_session_type, START_TEXT, INSPECT_CACHE

router = Router()

CONTACT_CACHE: dict[int, str] = {}

# =========================================================================
# 📩 READ OTP (1:1 ICE BOT)
# =========================================================================

@router.callback_query(F.data == "a_read_otp")
async def cb_a_read_otp(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_read_otp)
    text = """
📂 <b>📩 Read OTP</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send files (<code>.session</code>, <code>.zip</code>, <code>.json</code>, <code>.tdata</code>) or session string to read latest Telegram OTP.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_read_otp, F.text)
async def process_read_otp_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    raw_session = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()
    await execute_read_otp(message, raw_session)

async def execute_read_otp(message: Message, raw_session: str):
    prog = await message.answer("🔄 <i>Querying Telegram official notifications (777000)...</i>")
    stype = detect_session_type(raw_session)
    success, res = await read_latest_otp(raw_session, stype)

    if success:
        text = f"""
📩 <b>LATEST TELEGRAM OTP</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Account:</b> {res['user']}
📞 <b>Phone:</b> <code>{res['phone']}</code>
🔑 <b>OTP Code:</b> <code>{res['otp']}</code>
📅 <b>Received:</b> <code>{res['date']}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Full Message:</b>
<blockquote>{res['text']}</blockquote>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await prog.edit_text(text, reply_markup=back_to_main_keyboard())
    else:
        await prog.edit_text(f"❌ <b>Error:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

# =========================================================================
# 🔍 CHECK SESSIONS (HEALTH)
# =========================================================================

@router.callback_query(F.data.in_(["a_check", "tool_check_health"]))
async def cb_quick_health(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_health_session)
    text = """
📂 <b>🔍 Check Sessions</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send files (<code>.session</code>, <code>.zip</code>, <code>.json</code>, <code>.tdata</code>) or session string to begin.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_health_session, F.text)
async def process_quick_health_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    raw_session = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()
    await execute_health_check(message, raw_session)

async def execute_health_check(message: Message, raw_session: str):
    check_msg = await message.answer("🔄 <i>Testing session connection...</i>")
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

# =========================================================================
# 🛡️ SPAM CHECK
# =========================================================================

@router.callback_query(F.data.in_(["a_spam", "tool_check_spambot"]))
async def cb_tool_spambot(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_spambot_session)
    text = """
📂 <b>🛡️ Spam Check</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send files (<code>.session</code>, <code>.zip</code>, <code>.json</code>, <code>.tdata</code>) or session string to check account spam status.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_spambot_session, F.text)
async def process_spambot_session_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    raw_session = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()
    await execute_spambot_check(message, raw_session)

async def execute_spambot_check(message: Message, raw_session: str):
    prog_msg = await message.answer("🔄 <i>Querying @SpamBot... Please wait.</i>")
    success, res = await check_spambot_status(raw_session)
    if success:
        clean_status = "🟢 <b>CLEAN / NO LIMITS!</b>" if res.get("clean") else "🔴 <b>LIMITED / RESTRICTED!</b>"
        msg_text = f"""
🛡️ <b>SPAMBOT CHECK RESULT</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Status:</b> {clean_status}
📝 <b>Telegram SpamBot Response:</b>
<blockquote>{res.get('message', '')}</blockquote>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await prog_msg.edit_text(msg_text, reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Error checking SpamBot:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

# =========================================================================
# 📇 CONTACT TOOL
# =========================================================================

@router.callback_query(F.data == "a_contact")
async def cb_a_contact(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_contact)
    text = """
📂 <b>📇 Contact Tool</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send files (<code>.session</code>, <code>.zip</code>, <code>.json</code>) or session string to inspect or clean account contacts.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_contact, F.text)
async def process_contact_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    raw_session = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()
    await execute_contact_tool(message, raw_session)

async def execute_contact_tool(message: Message, raw_session: str):
    prog = await message.answer("🔄 <i>Scanning account synced contacts...</i>")
    success, res = await manage_contacts(raw_session, "count")
    if success:
        user_id = message.from_user.id
        CONTACT_CACHE[user_id] = raw_session
        cnt = res.get("count", 0)
        text = f"""
📇 <b>CONTACT TOOL REPORT</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 <b>Total Synced Contacts:</b> <code>{cnt}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You can clean and delete all contacts linked to this Telegram account below:
"""
        btns = [
            [InlineKeyboardButton(text="🗑️ Delete All Contacts", callback_data="action_delete_contacts")],
            [InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op")]
        ]
        await prog.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    else:
        await prog.edit_text(f"❌ <b>Failed to fetch contacts:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

@router.callback_query(F.data == "action_delete_contacts")
async def cb_action_del_contacts(query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in CONTACT_CACHE:
        await query.answer("Session expired from cache. Please re-send.", show_alert=True)
        return
    raw_session = CONTACT_CACHE[user_id]
    await query.answer("Deleting contacts...", show_alert=False)
    prog = await query.message.edit_text("⏳ <i>Deleting all synced contacts from account...</i>")
    success, res = await manage_contacts(raw_session, "delete")
    if success:
        await prog.edit_text(f"🎉 <b>CONTACTS CLEARED!</b>\n\n✅ {res}", reply_markup=back_to_main_keyboard())
    else:
        await prog.edit_text(f"❌ <b>Failed to delete contacts:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

# =========================================================================
# 🔐 2FA MANAGER
# =========================================================================

@router.callback_query(F.data.in_(["a_2fa", "tool_check_2fa"]))
async def cb_a_2fa(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_2fa_session)
    text = """
📂 <b>🔐 2FA Manager</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send files (<code>.session</code>, <code>.zip</code>, <code>.json</code>) or session string to check or manage Two-Step Verification.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_2fa_session, F.text)
async def process_2fa_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    raw_session = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()
    await execute_2fa_check(message, raw_session)

async def execute_2fa_check(message: Message, raw_session: str):
    prog_msg = await message.answer("🔄 <i>Auditing 2FA Security... Please wait.</i>")
    stype = detect_session_type(raw_session)
    success, res = await check_2fa_status(raw_session, stype)

    if success:
        has_2fa = res.get("has_2fa")
        badge = "🟢 <b>ENABLED (Protected)</b>" if has_2fa else "🔴 <b>DISABLED (High Risk!)</b>"
        hint = res.get("hint") or "None"
        rec = "✅ Yes" if res.get("has_recovery") else "❌ None"

        text = f"""
🔐 <b>2FA SECURITY AUDIT RESULT</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛡️ <b>2FA Status:</b> {badge}
🔑 <b>Password Hint:</b> <code>{hint}</code>
📧 <b>Recovery Email:</b> {rec}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Always keep 2FA enabled on your Telegram accounts to prevent unauthorized access.</i>
"""
        await prog_msg.edit_text(text, reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Failed to check 2FA:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

# =========================================================================
# ✂️ SPLIT FILE
# =========================================================================

@router.callback_query(F.data == "a_split")
async def cb_a_split(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_split)
    text = """
📂 <b>✂️ Split File</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send a <code>.zip</code> archive or multi-session file to split into separate sessions.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_split, F.text)
async def process_split_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    text = message.text.strip()
    await state.clear()
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 40]
    if not lines:
        await message.reply("❌ No valid sessions detected in text.", reply_markup=back_to_main_keyboard())
        return

    files_dict = {}
    for idx, s in enumerate(lines, 1):
        stype = detect_session_type(s)
        ext = "telethon" if stype == "telethon" else "pyrogram"
        files_dict[f"session_{idx}_{ext}.session"] = s

    zip_bytes = create_zip_archive(files_dict)
    doc = BufferedInputFile(zip_bytes, filename="split_sessions.zip")
    await message.answer_document(
        doc,
        caption=f"✂️ <b>SPLIT COMPLETE!</b>\nExtracted <code>{len(files_dict)}</code> individual sessions.",
        reply_markup=back_to_main_keyboard()
    )

# =========================================================================
# 🔗 SESSION API LINK
# =========================================================================

@router.callback_query(F.data == "cv_s2api")
async def cb_cv_s2api(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_api_link)
    text = """
📂 <b>🔗 Session API Link</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send files (<code>.session</code>, <code>.json</code>) or session string to extract or link API credentials.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_api_link, F.text)
async def process_api_link_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    raw_session = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()
    await execute_api_link(message, raw_session)

async def execute_api_link(message: Message, raw_session: str):
    prog = await message.answer("🔄 <i>Extracting API credentials and profile links...</i>")
    stype = detect_session_type(raw_session)
    health = await check_session_health(raw_session, stype)

    user_id = health.get("user_id") or "Unknown"
    dc_id = health.get("dc_id") or "1"
    name = health.get("name") or "Telegram Account"

    text = f"""
🔗 <b>SESSION API CONFIGURATION & LINK</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Account:</b> {name}
🆔 <b>User ID:</b> <code>{user_id}</code>
🌐 <b>Data Center:</b> DC {dc_id}
⚡ <b>Library Engine:</b> <code>{stype.upper()}</code>
🔑 <b>Default API ID:</b> <code>{config.API_ID}</code>
🗝️ <b>Default API HASH:</b> <code>{config.API_HASH}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 <b>Telegram Developer Apps Portal:</b>
https://my.telegram.org/apps
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await prog.edit_text(text, reply_markup=back_to_main_keyboard(), disable_web_page_preview=True)

# =========================================================================
# 📦 MERGE FILES
# =========================================================================

@router.callback_query(F.data == "merge_start")
async def cb_merge_start(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_merge)
    text = """
📂 <b>📦 Merge Files</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send <code>.session</code> or <code>.json</code> files (or multiple sessions) to merge into a single consolidated archive.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_merge, F.text)
async def process_merge_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    text = message.text.strip()
    await state.clear()
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 40]
    if not lines:
        await message.reply("❌ No valid sessions found to merge.", reply_markup=back_to_main_keyboard())
        return

    files_dict = {}
    for idx, s in enumerate(lines, 1):
        files_dict[f"merged_session_{idx}.session"] = s

    files_dict["manifest.json"] = f'{{"total_sessions": {len(files_dict)}}}'
    zip_bytes = create_zip_archive(files_dict)
    doc = BufferedInputFile(zip_bytes, filename="merged_sessions.zip")
    await message.answer_document(
        doc,
        caption=f"📦 <b>MERGE COMPLETE!</b>\nConsolidated <code>{len(lines)}</code> sessions into single archive.",
        reply_markup=back_to_main_keyboard()
    )

# =========================================================================
# 👁️ PRIVACY SETTINGS AUDIT
# =========================================================================

@router.callback_query(F.data.in_(["a_privacy", "tool_privacy"]))
async def cb_tool_privacy(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_privacy_session)
    text = """
📂 <b>👁️ Privacy Settings</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send files (<code>.session</code>, <code>.zip</code>, <code>.json</code>) or session string to audit account privacy settings.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_privacy_session, F.text)
async def process_privacy_session_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    raw_session = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()
    await execute_privacy_check(message, raw_session)

async def execute_privacy_check(message: Message, raw_session: str):
    prog_msg = await message.answer("🔍 <i>Fetching Privacy Settings...</i>")
    success, res = await check_account_privacy(raw_session)

    if success:
        text = f"""
👁️ <b>ACCOUNT PRIVACY REPORT</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📞 <b>Phone Number:</b> {res['phone_privacy']}
🕒 <b>Last Seen & Online:</b> {res['last_seen_privacy']}
🖼️ <b>Profile Photo:</b> {res['photo_privacy']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await prog_msg.edit_text(text, reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Failed to fetch privacy:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

# =========================================================================
# 📅 CHECK AGE
# =========================================================================

@router.callback_query(F.data.in_(["a_age", "tool_check_age"]))
async def cb_tool_check_age(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_age_session)
    text = """
📂 <b>📅 Check Age</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send Telegram User ID or session file (<code>.session</code>, <code>.zip</code>, <code>.json</code>) to check registration date.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_age_session, F.text)
async def process_age_session_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    val = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()
    await execute_age_check(message, val)

async def execute_age_check(message: Message, val: str):
    user_id = None
    if val.isdigit():
        user_id = int(val)
    else:
        stype = detect_session_type(val)
        health = await check_session_health(val, stype)
        if health.get("status") == "alive" and health.get("user_id"):
            user_id = health["user_id"]
        else:
            await message.reply("❌ Invalid Session or User ID! Please check and try again.", reply_markup=back_to_main_keyboard())
            return

    res = estimate_account_age(user_id)
    text = f"""
📅 <b>ACCOUNT AGE ESTIMATE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🆔 <b>User ID:</b> <code>{res['user_id']}</code>
🗓️ <b>Created Around:</b> <b>{res['period']}</b>
🏆 <b>Account Tier:</b> {res['description']}
💎 <b>Collector Status:</b> {res['rarity']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await message.answer(text, reply_markup=back_to_main_keyboard())

# =========================================================================
# 🔀 CONVERTER
# =========================================================================

@router.callback_query(F.data.in_(["a_convert", "tool_converter"]))
async def cb_tool_converter(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_convert_session)
    text = """
📂 <b>🔀 Session Converter</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send files (<code>.session</code>, <code>.json</code>) or session string to convert between Pyrogram and Telethon format.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_convert_session, F.text)
async def process_convert_session_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    raw_session = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()
    await execute_converter(message, raw_session)

async def execute_converter(message: Message, raw_session: str):
    prog_msg = await message.answer("🔄 <i>Converting session format...</i>")
    success, res = await convert_session(raw_session)

    if success:
        text = f"""
🎉 <b>SESSION CONVERTED SUCCESSFULLY!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 <b>From:</b> <code>{res['from_type']}</code>
➡️ <b>To:</b> <code>{res['to_type']}</code>
👤 <b>Account:</b> {res.get('user', 'Telegram User')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<code>{res['result']}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <i>Click above to copy. Keep this confidential!</i>
"""
        await prog_msg.edit_text(text, reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Conversion failed:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

# =========================================================================
# 🚪 LEAVE GROUPS & CHANNELS
# =========================================================================

@router.callback_query(F.data.in_(["c_leavegc", "tool_leave_chats"]))
async def cb_tool_leave(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_leave_session)
    text = """
📂 <b>🚪 Leave Groups & Channels</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send files (<code>.session</code>, <code>.zip</code>, <code>.json</code>) or session string to leave all channels and groups.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_leave_session, F.text)
async def process_leave_session_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    raw_session = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()
    await execute_leave_chats(message, raw_session)

async def execute_leave_chats(message: Message, raw_session: str):
    stype = detect_session_type(raw_session)
    prog_msg = await message.answer("⏳ <i>Leaving channels and groups... This might take a moment.</i>")
    success, res = await leave_all_dialogs(raw_session, stype)
    if success:
        await prog_msg.edit_text(f"🎉 <b>CLEANUP COMPLETE!</b>\n\n✅ {res}", reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Failed:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

# =========================================================================
# 🗑️ CLEAR DATA (DELETE ALL DIALOGS)
# =========================================================================

@router.callback_query(F.data.in_(["a_clear", "tool_delete_dialogs"]))
async def cb_tool_delete_dialogs(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_delete_dialogs_session)
    text = """
📂 <b>🗑️ Clear Data</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ <b>Waiting for files...</b>

Please send files (<code>.session</code>, <code>.zip</code>, <code>.json</code>) or session string to delete all private dialogs and chats.
""".strip()
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_delete_dialogs_session, F.text)
async def process_delete_dialogs_text(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    raw_session = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()
    await execute_delete_dialogs(message, raw_session)

async def execute_delete_dialogs(message: Message, raw_session: str):
    prog_msg = await message.answer("⏳ <i>Deleting private chats and dialogs... Please wait.</i>")
    success, res = await delete_all_dialogs(raw_session)
    if success:
        await prog_msg.edit_text(f"🎉 <b>CLEANUP COMPLETE!</b>\n\n✅ {res}", reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Failed:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

# =========================================================================
# 👤 USER CENTER (1:1 ICE BOT)
# =========================================================================

@router.callback_query(F.data.in_(["user_center", "tool_user_center"]))
async def cb_user_center(query: CallbackQuery):
    user = query.from_user
    acc_count = await db.count_user_accounts(user.id)
    text = f"""
✨ <b>ICE BOT • USER CENTER</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>User:</b> {user.first_name}
🆔 <b>User ID:</b> <code>{user.id}</code>
🔗 <b>Username:</b> @{user.username or 'None'}
🟢 <b>Plan:</b> Free Unlimited
💼 <b>Vault Sessions:</b> <code>{acc_count}</code>
🛡️ <b>Security:</b> AES-256 Cloud Encrypted
🌐 <b>Language:</b> English
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await query.message.edit_text(text, reply_markup=user_center_keyboard())

# =========================================================================
# 🆘 CUSTOMER SUPPORT (1:1 ICE BOT)
# =========================================================================

@router.callback_query(F.data == "support_contact")
async def cb_support_contact(query: CallbackQuery):
    text = """
🆘 <b>Customer Support</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Need assistance or having issues?
Our support team is available 24/7.

• <b>Official Bot:</b> @SessionManagerVoltxbot
• <b>Channel:</b> @SessionManagerUpdates
• <b>Status:</b> 🟢 Systems Fully Operational
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

# =========================================================================
# 🌐 LANGUAGE SETTINGS (1:1 ICE BOT)
# =========================================================================

@router.callback_query(F.data == "lang_menu")
async def cb_lang_menu(query: CallbackQuery):
    text = """
🌐 <b>Language Settings</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please select your preferred language:
"""
    await query.message.edit_text(text, reply_markup=language_keyboard())

@router.callback_query(F.data.startswith("lang_set:"))
async def cb_lang_set(query: CallbackQuery):
    lang = query.data.split(":")[1]
    lang_names = {
        "en": "English",
        "zh": "中文",
        "ru": "Русский",
        "bn": "বাংলা",
        "vi": "Tiếng Việt"
    }
    await query.answer(f"Language set to {lang_names.get(lang, lang)}! 🌐", show_alert=True)
    user = query.from_user
    acc_count = await db.count_user_accounts(user.id)
    await query.message.edit_text(
        START_TEXT,
        reply_markup=main_menu_keyboard(config.OWNER_ID, user.id, acc_count),
        disable_web_page_preview=True
    )

# =========================================================================
# 📱 DEVICE FINGERPRINTS & CLONER
# =========================================================================

@router.callback_query(F.data == "tool_fingerprints")
async def cb_tool_fingerprints(query: CallbackQuery):
    text = """
📱 <b>DEVICE FINGERPRINTS & CLONER SUITE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Select any hardware profile to inspect or generate authentic device sessions:
"""
    await query.message.edit_text(text, reply_markup=fingerprints_selector_keyboard("view"))

@router.callback_query(F.data.startswith("fpview_"))
async def cb_fpview(query: CallbackQuery):
    dev_key = query.data.split("_")[1]
    fp = DEVICE_FINGERPRINTS.get(dev_key, DEVICE_FINGERPRINTS["default"])
    text = f"""
{fp['icon']} <b>HARDWARE PROFILE: {fp['name']}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 <b>Device Model:</b> <code>{fp['device_model']}</code>
💻 <b>System Version:</b> <code>{fp['system_version']}</code>
📦 <b>App Version:</b> <code>{fp['app_version']}</code>
🌐 <b>Language Code:</b> <code>{fp['lang_code']} ({fp['system_lang_code']})</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Is fingerprint se generate kiya hua session Telegram settings me issi real device ke roop me appear hoga.</i>
"""
    buttons = [
        [InlineKeyboardButton(text=f"⚡ Generate Session with {fp['name'][:18]}", callback_data=f"fpgen_{dev_key}")],
        [InlineKeyboardButton(text="🔙 Back to Devices", callback_data="tool_fingerprints")],
        [InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# =========================================================================
# 📥 UNIVERSAL DOCUMENT / FILE UPLOADER (.session, .zip, .json, .txt)
# =========================================================================

@router.message(F.document)
async def handle_document_upload(message: Message, state: FSMContext):
    doc = message.document
    fn = doc.file_name or "uploaded_file"

    status_msg = await message.reply("📥 <i>Downloading and parsing file(s)...</i>")
    try:
        file_obj = await message.bot.get_file(doc.file_id)
        stream = await message.bot.download_file(file_obj.file_path)
        raw_bytes = stream.read()

        sessions = extract_all_sessions_from_bytes(fn, raw_bytes)
        if not sessions:
            await status_msg.edit_text(
                "❌ <b>No valid Telegram session found in the uploaded file.</b>\n"
                "Please upload a valid <code>.session</code>, <code>.zip</code>, or <code>.json</code> file.",
                reply_markup=back_to_main_keyboard()
            )
            return

        current_state = await state.get_state()

        # 1. State: Read OTP
        if current_state == ToolStates.waiting_read_otp.state:
            await state.clear()
            await status_msg.delete()
            await execute_read_otp(message, sessions[0]["session"])
            return

        # 2. State: Check Sessions Health
        elif current_state == ToolStates.waiting_health_session.state:
            await state.clear()
            if len(sessions) == 1:
                await status_msg.delete()
                await execute_health_check(message, sessions[0]["session"])
                return
            else:
                # Batch health check
                await status_msg.edit_text(f"⏳ <i>Testing {len(sessions)} sessions in batch...</i>")
                alive_cnt = 0
                dead_cnt = 0
                for item in sessions:
                    h = await check_session_health(item["session"], item["type"])
                    if h.get("status") == "alive":
                        alive_cnt += 1
                    else:
                        dead_cnt += 1
                text = f"""
📊 <b>BATCH SESSION HEALTH REPORT</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 <b>Total Processed:</b> <code>{len(sessions)}</code>
🟢 <b>Alive & Active:</b> <code>{alive_cnt}</code>
🔴 <b>Dead / Revoked:</b> <code>{dead_cnt}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                await status_msg.edit_text(text, reply_markup=back_to_main_keyboard())
                return

        # 3. State: Spam Check
        elif current_state == ToolStates.waiting_spambot_session.state:
            await state.clear()
            await status_msg.delete()
            await execute_spambot_check(message, sessions[0]["session"])
            return

        # 4. State: Contact Tool
        elif current_state == ToolStates.waiting_contact.state:
            await state.clear()
            await status_msg.delete()
            await execute_contact_tool(message, sessions[0]["session"])
            return

        # 5. State: 2FA Manager
        elif current_state == ToolStates.waiting_2fa_session.state:
            await state.clear()
            await status_msg.delete()
            await execute_2fa_check(message, sessions[0]["session"])
            return

        # 6. State: Split File
        elif current_state == ToolStates.waiting_split.state:
            await state.clear()
            files_dict = {}
            for idx, s in enumerate(sessions, 1):
                ext = "telethon" if s["type"] == "telethon" else "pyrogram"
                files_dict[f"session_{idx}_{ext}.session"] = s["session"]
            zip_bytes = create_zip_archive(files_dict)
            doc_out = BufferedInputFile(zip_bytes, filename="split_sessions.zip")
            await status_msg.delete()
            await message.answer_document(
                doc_out,
                caption=f"✂️ <b>SPLIT COMPLETE!</b>\nExtracted <code>{len(files_dict)}</code> individual sessions.",
                reply_markup=back_to_main_keyboard()
            )
            return

        # 7. State: Session API Link
        elif current_state == ToolStates.waiting_api_link.state:
            await state.clear()
            await status_msg.delete()
            await execute_api_link(message, sessions[0]["session"])
            return

        # 8. State: Merge Files
        elif current_state == ToolStates.waiting_merge.state:
            await state.clear()
            files_dict = {}
            for idx, s in enumerate(sessions, 1):
                files_dict[f"merged_session_{idx}.session"] = s["session"]
            files_dict["manifest.json"] = f'{{"total_sessions": {len(files_dict)}}}'
            zip_bytes = create_zip_archive(files_dict)
            doc_out = BufferedInputFile(zip_bytes, filename="merged_sessions.zip")
            await status_msg.delete()
            await message.answer_document(
                doc_out,
                caption=f"📦 <b>MERGE COMPLETE!</b>\nConsolidated <code>{len(sessions)}</code> sessions into single archive.",
                reply_markup=back_to_main_keyboard()
            )
            return

        # 9. State: Privacy Settings
        elif current_state == ToolStates.waiting_privacy_session.state:
            await state.clear()
            await status_msg.delete()
            await execute_privacy_check(message, sessions[0]["session"])
            return

        # 10. State: Check Age
        elif current_state == ToolStates.waiting_age_session.state:
            await state.clear()
            await status_msg.delete()
            await execute_age_check(message, sessions[0]["session"])
            return

        # 11. State: Converter
        elif current_state == ToolStates.waiting_convert_session.state:
            await state.clear()
            await status_msg.delete()
            await execute_converter(message, sessions[0]["session"])
            return

        # 12. State: Leave Groups & Channels
        elif current_state == ToolStates.waiting_leave_session.state:
            await state.clear()
            await status_msg.delete()
            await execute_leave_chats(message, sessions[0]["session"])
            return

        # 13. State: Clear Data
        elif current_state == ToolStates.waiting_delete_dialogs_session.state:
            await state.clear()
            await status_msg.delete()
            await execute_delete_dialogs(message, sessions[0]["session"])
            return

        # 14. State: Devices & Terminate
        elif current_state == DeviceStates.waiting_session.state:
            from handlers.devices import show_devices_view
            await state.clear()
            await status_msg.delete()
            await show_devices_view(message.from_user.id, message, sessions[0]["session"], sessions[0]["type"])
            return

        # 15. Default (Main Menu Direct Upload): Health Check & Save to Vault
        else:
            saved_cnt = 0
            for s in sessions:
                h = await check_session_health(s["session"], s["type"])
                if h.get("status") == "alive":
                    await db.save_account(
                        user_id=message.from_user.id,
                        session_type=s["type"],
                        account_name=h.get("name") or s["filename"],
                        phone=h.get("phone") or "File Account",
                        tg_user_id=h.get("user_id") or 0,
                        raw_session=s["session"]
                    )
                    saved_cnt += 1

            if len(sessions) == 1:
                first = sessions[0]
                h = await check_session_health(first["session"], first["type"])
                if h.get("status") == "alive":
                    text = f"""
🎉 <b>FILE PARSED & SAVED TO VAULT!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 <b>Filename:</b> <code>{fn}</code>
👤 <b>Name:</b> {h['name']}
📞 <b>Phone:</b> <code>{h['phone']}</code>
⚡ <b>Engine:</b> <code>{first['type'].upper()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                else:
                    text = f"❌ <b>Session in file is dead/invalid:</b> <code>{h.get('error')}</code>"
            else:
                text = f"""
🎉 <b>BATCH UPLOAD COMPLETE!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 <b>Total Found:</b> <code>{len(sessions)}</code>
🟢 <b>Alive & Saved to Vault:</b> <code>{saved_cnt}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            btns = [
                [InlineKeyboardButton(text="💼 Open Encrypted Vault", callback_data="menu_vault")],
                [InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op")]
            ]
            await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

    except Exception as e:
        await status_msg.edit_text(f"❌ Error processing file: <code>{e}</code>", reply_markup=back_to_main_keyboard())
