from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db
from helpers.keyboard import (
    tools_menu_keyboard, session_source_keyboard, cancel_keyboard,
    back_to_main_keyboard, fingerprints_selector_keyboard, user_center_keyboard
)
from helpers.states import ToolStates
from helpers.session_tools import (
    leave_all_dialogs, check_session_health,
    check_2fa_status, get_account_full_info,
    check_spambot_status, delete_all_dialogs,
    DEVICE_FINGERPRINTS, estimate_account_age,
    check_account_privacy, convert_session
)
from handlers.common import detect_session_type

router = Router()

@router.callback_query(F.data == "menu_tools")
async def cb_menu_tools(query: CallbackQuery, state: FSMContext):
    await state.clear()
    text = """
╭━━━━━━━━━━━━━━━━━━━━╮
│  🛠 <b>ᴀᴄᴄᴏᴜɴᴛ ᴜᴛɪʟɪᴛʏ ᴛᴏᴏʟs</b>  │
╰━━━━━━━━━━━━━━━━━━━━╯
Yahan se aap apne account par batch operations kar sakte hain:

🚪 <b>Leave All Chats:</b> Saare joined channels aur groups se turant exit karein.
🔍 <b>Quick Health Check:</b> Kisi bhi string session ko paste karke check karein ki wo valid hai ya banned.
"""
    await query.message.edit_text(text, reply_markup=tools_menu_keyboard())

@router.callback_query(F.data == "tool_leave_chats")
async def cb_tool_leave(query: CallbackQuery, state: FSMContext):
    text = """
🚪 <b>LEAVE ALL CHANNELS & GROUPS</b>

Aap session string paste karna chahte hain ya apne saved vault se select karna chahte hain?
"""
    await query.message.edit_text(text, reply_markup=session_source_keyboard("leave"))

@router.callback_query(F.data == "src_paste_leave")
async def cb_paste_leave(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_leave_session)
    await query.message.edit_text(
        "📝 <b>Send String Session to leave all channels & groups:</b>\n\n"
        "<i>(Session will be deleted immediately)</i>\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_keyboard()
    )

@router.message(ToolStates.waiting_leave_session)
async def process_leave_session(message: Message, state: FSMContext):
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
    prog_msg = await message.answer("⏳ <i>Leaving channels and groups... This might take a moment.</i>")
    success, res = await leave_all_dialogs(raw_session, stype)
    if success:
        await prog_msg.edit_text(f"🎉 <b>CLEANUP COMPLETE!</b>\n\n✅ {res}", reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Failed:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

@router.callback_query(F.data == "src_vault_leave")
async def cb_vault_leave(query: CallbackQuery):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    if not accounts:
        await query.answer("Aapke vault me koi account nahi hai!", show_alert=True)
        return

    buttons = []
    for acc in accounts:
        btn_text = f"👤 {acc['account_name']} ({acc['session_type'].capitalize()})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"selleave_acc_{acc['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="menu_tools")])

    await query.message.edit_text("💼 <b>Select an account:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("selleave_acc_"))
async def cb_selleave_exec(query: CallbackQuery):
    acc_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    account = await db.get_account(acc_id, user_id)
    if not account:
        await query.answer("Account not found!", show_alert=True)
        return

    prog_msg = await query.message.edit_text("⏳ <i>Leaving channels and groups...</i>")
    success, res = await leave_all_dialogs(account["raw_session"], account["session_type"])
    if success:
        await prog_msg.edit_text(f"🎉 <b>CLEANUP COMPLETE!</b>\n\n✅ {res}", reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Failed:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

@router.callback_query(F.data == "tool_check_health")
async def cb_quick_health(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_health_session)
    await query.message.edit_text(
        "🔍 <b>QUICK SESSION HEALTH CHECK</b>\n\n"
        "Send any Pyrogram or Telethon string session to inspect its live status:\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_keyboard()
    )

@router.message(ToolStates.waiting_health_session)
async def process_quick_health(message: Message, state: FSMContext):
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
# 🗑️ DELETE ALL DIALOGS (CLEAN ACCOUNT)
# =========================================================================

@router.callback_query(F.data == "tool_delete_dialogs")
async def cb_tool_delete_dialogs(query: CallbackQuery, state: FSMContext):
    text = """
🗑️ <b>DELETE ALL DIALOGS & PRIVATE CHATS</b>

Aap session string paste karna chahte hain ya apne saved vault se select karna chahte hain?
"""
    await query.message.edit_text(text, reply_markup=session_source_keyboard("deldialogs"))

@router.callback_query(F.data == "src_paste_deldialogs")
async def cb_paste_deldialogs(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_delete_dialogs_session)
    await query.message.edit_text(
        "📝 <b>Send String Session to clear all private chats/dialogs:</b>\n\n"
        "<i>(Session will be deleted immediately for privacy)</i>\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_keyboard()
    )

@router.message(ToolStates.waiting_delete_dialogs_session)
async def process_delete_dialogs_session(message: Message, state: FSMContext):
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

    prog_msg = await message.answer("⏳ <i>Deleting private chats and dialogs... Please wait.</i>")
    from helpers.session_tools import delete_all_dialogs
    success, res = await delete_all_dialogs(raw_session)
    if success:
        await prog_msg.edit_text(f"🎉 <b>CLEANUP COMPLETE!</b>\n\n✅ {res}", reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Failed:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

@router.callback_query(F.data == "src_vault_deldialogs")
async def cb_vault_deldialogs(query: CallbackQuery):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    if not accounts:
        await query.answer("Aapke vault me koi account nahi hai!", show_alert=True)
        return

    buttons = []
    for acc in accounts:
        btn_text = f"👤 {acc['account_name']} ({acc['session_type'].capitalize()})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"seldeldia_acc_{acc['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="menu_tools")])

    await query.message.edit_text("💼 <b>Select an account:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("seldeldia_acc_"))
async def cb_seldeldia_exec(query: CallbackQuery):
    acc_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    account = await db.get_account(acc_id, user_id)
    if not account:
        await query.answer("Account not found!", show_alert=True)
        return

    prog_msg = await query.message.edit_text("⏳ <i>Deleting private chats and dialogs...</i>")
    from helpers.session_tools import delete_all_dialogs
    success, res = await delete_all_dialogs(account["raw_session"])
    if success:
        await prog_msg.edit_text(f"🎉 <b>CLEANUP COMPLETE!</b>\n\n✅ {res}", reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Failed:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

# =========================================================================
# 🛡️ CHECK SPAMBOT / BAN STATUS
# =========================================================================

@router.callback_query(F.data == "tool_check_spambot")
async def cb_tool_spambot(query: CallbackQuery, state: FSMContext):
    text = """
🛡️ <b>CHECK BAN & SPAMBOT STATUS</b>

Aap session string paste karna chahte hain ya apne saved vault se select karna chahte hain?
"""
    await query.message.edit_text(text, reply_markup=session_source_keyboard("spambot"))

@router.callback_query(F.data == "src_paste_spambot")
async def cb_paste_spambot(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_spambot_session)
    await query.message.edit_text(
        "📝 <b>Send String Session to check SpamBot limitation:</b>\n\n"
        "<i>(Session will be deleted immediately for privacy)</i>\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_keyboard()
    )

@router.message(ToolStates.waiting_spambot_session)
async def process_spambot_session(message: Message, state: FSMContext):
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

    prog_msg = await message.answer("🔄 <i>Querying @SpamBot... Please wait.</i>")
    from helpers.session_tools import check_spambot_status
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

@router.callback_query(F.data == "src_vault_spambot")
async def cb_vault_spambot(query: CallbackQuery):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    if not accounts:
        await query.answer("Aapke vault me koi account nahi hai!", show_alert=True)
        return

    buttons = []
    for acc in accounts:
        btn_text = f"👤 {acc['account_name']} ({acc['session_type'].capitalize()})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"selspam_acc_{acc['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="menu_tools")])

    await query.message.edit_text("💼 <b>Select an account:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("selspam_acc_"))
async def cb_selspam_exec(query: CallbackQuery):
    acc_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    account = await db.get_account(acc_id, user_id)
    if not account:
        await query.answer("Account not found!", show_alert=True)
        return

    prog_msg = await query.message.edit_text("🔄 <i>Querying @SpamBot...</i>")
    from helpers.session_tools import check_spambot_status
    success, res = await check_spambot_status(account["raw_session"])
    if success:
        clean_status = "🟢 <b>CLEAN / NO LIMITS!</b>" if res.get("clean") else "🔴 <b>LIMITED / RESTRICTED!</b>"
        msg_text = f"""
🛡️ <b>SPAMBOT CHECK RESULT: {account['account_name']}</b>

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
# 🔐 2FA SECURITY AUDIT
# =========================================================================

@router.callback_query(F.data == "tool_check_2fa")
async def cb_tool_2fa(query: CallbackQuery, state: FSMContext):
    await state.clear()
    text = """
🔐 <b>TWO-STEP VERIFICATION (2FA) AUDIT</b>

Aap session string paste karna chahte hain ya apne saved vault se select karna chahte hain?
"""
    await query.message.edit_text(text, reply_markup=session_source_keyboard("2fa"))

@router.callback_query(F.data == "src_paste_2fa")
async def cb_paste_2fa(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_2fa_session)
    await query.message.edit_text(
        "📝 <b>Send String Session to check 2FA status:</b>\n\n"
        "<i>(Your session string will be deleted immediately from chat)</i>\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_keyboard()
    )

@router.message(ToolStates.waiting_2fa_session)
async def process_2fa_session(message: Message, state: FSMContext):
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
💡 <i>Tip: Always keep 2FA enabled on your Telegram accounts to prevent unauthorized access.</i>
"""
        await prog_msg.edit_text(text, reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Failed to check 2FA:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

@router.callback_query(F.data == "src_vault_2fa")
async def cb_vault_2fa(query: CallbackQuery):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    if not accounts:
        await query.answer("Aapke vault me koi account nahi hai!", show_alert=True)
        return

    buttons = []
    for acc in accounts:
        btn_text = f"👤 {acc['account_name']} ({acc['session_type'].capitalize()})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"sel2fa_acc_{acc['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_main")])

    await query.message.edit_text("💼 <b>Select an account from your Vault:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("sel2fa_acc_"))
async def cb_sel2fa_exec(query: CallbackQuery):
    acc_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    account = await db.get_account(acc_id, user_id)
    if not account:
        await query.answer("Account not found!", show_alert=True)
        return

    prog_msg = await query.message.edit_text("🔄 <i>Auditing 2FA Security...</i>")
    success, res = await check_2fa_status(account["raw_session"], account["session_type"])

    if success:
        has_2fa = res.get("has_2fa")
        badge = "🟢 <b>ENABLED (Protected)</b>" if has_2fa else "🔴 <b>DISABLED (High Risk!)</b>"
        hint = res.get("hint") or "None"
        rec = "✅ Yes" if res.get("has_recovery") else "❌ None"

        text = f"""
🔐 <b>2FA SECURITY AUDIT: {account['account_name']}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛡️ <b>2FA Status:</b> {badge}
🔑 <b>Password Hint:</b> <code>{hint}</code>
📧 <b>Recovery Email:</b> {rec}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await prog_msg.edit_text(text, reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Failed:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())


# =========================================================================
# 👤 ACCOUNT FULL INFO INSPECTOR
# =========================================================================

@router.callback_query(F.data == "tool_acc_info")
async def cb_tool_acc_info(query: CallbackQuery, state: FSMContext):
    await state.clear()
    text = """
👤 <b>ACCOUNT FULL INFO INSPECTOR</b>

Aap session string paste karna chahte hain ya apne saved vault se select karna chahte hain?
"""
    await query.message.edit_text(text, reply_markup=session_source_keyboard("info"))

@router.callback_query(F.data == "src_paste_info")
async def cb_paste_info(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_info_session)
    await query.message.edit_text(
        "📝 <b>Send String Session to inspect full account details:</b>\n\n"
        "<i>(Your session string will be deleted immediately for privacy)</i>\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_keyboard()
    )

@router.message(ToolStates.waiting_info_session)
async def process_info_session(message: Message, state: FSMContext):
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

    prog_msg = await message.answer("🔍 <i>Fetching comprehensive account details...</i>")
    stype = detect_session_type(raw_session)
    success, info = await get_account_full_info(raw_session, stype)

    if success:
        prem = "⭐️ Yes (Telegram Premium)" if info["is_premium"] else "No"
        two_fa = "🟢 Enabled" if info["has_2fa"] else "🔴 Disabled"
        text = f"""
❄️ <b>ACCOUNT INTELLIGENCE REPORT</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Name:</b> {info['name']}
🆔 <b>User ID:</b> <code>{info['user_id']}</code>
🔗 <b>Username:</b> @{info['username']}
📞 <b>Phone:</b> <code>{info['phone']}</code>
🌐 <b>Data Center:</b> DC {info['dc_id']}
💎 <b>Premium:</b> {prem}
🔐 <b>2FA Security:</b> {two_fa}
📱 <b>Active Devices:</b> <code>{info['active_sessions']}</code>
📁 <b>Joined Channels/Groups:</b> <code>{info['channels_count']}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await prog_msg.edit_text(text, reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Error:</b> <code>{info}</code>", reply_markup=back_to_main_keyboard())

@router.callback_query(F.data == "src_vault_info")
async def cb_vault_info(query: CallbackQuery):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    if not accounts:
        await query.answer("Aapke vault me koi account nahi hai!", show_alert=True)
        return

    buttons = []
    for acc in accounts:
        btn_text = f"👤 {acc['account_name']} ({acc['session_type'].capitalize()})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"selinfo_acc_{acc['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_main")])

    await query.message.edit_text("💼 <b>Select an account from your Vault:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("selinfo_acc_"))
async def cb_selinfo_exec(query: CallbackQuery):
    acc_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    account = await db.get_account(acc_id, user_id)
    if not account:
        await query.answer("Account not found!", show_alert=True)
        return

    prog_msg = await query.message.edit_text("🔍 <i>Fetching comprehensive account details...</i>")
    success, info = await get_account_full_info(account["raw_session"], account["session_type"])

    if success:
        prem = "⭐️ Yes (Telegram Premium)" if info["is_premium"] else "No"
        two_fa = "🟢 Enabled" if info["has_2fa"] else "🔴 Disabled"
        text = f"""
❄️ <b>ACCOUNT INTELLIGENCE REPORT: {account['account_name']}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Name:</b> {info['name']}
🆔 <b>User ID:</b> <code>{info['user_id']}</code>
🔗 <b>Username:</b> @{info['username']}
📞 <b>Phone:</b> <code>{info['phone']}</code>
🌐 <b>Data Center:</b> DC {info['dc_id']}
💎 <b>Premium:</b> {prem}
🔐 <b>2FA Security:</b> {two_fa}
📱 <b>Active Devices:</b> <code>{info['active_sessions']}</code>
📁 <b>Joined Channels/Groups:</b> <code>{info['channels_count']}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await prog_msg.edit_text(text, reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Error:</b> <code>{info}</code>", reply_markup=back_to_main_keyboard())


# =========================================================================
# 🔑 EXPORT SINGLE SESSION STRING
# =========================================================================

@router.callback_query(F.data.startswith("acc_export_"))
async def cb_acc_export(query: CallbackQuery):
    acc_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    account = await db.get_account(acc_id, user_id)
    if not account:
        await query.answer("Account not found!", show_alert=True)
        return

    s = account.get("raw_session") or account.get("session_string", "")
    text = f"""
🔑 <b>SESSION STRING: {account['account_name']}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <b>Type:</b> <code>{account['session_type'].upper()}</code>
📞 <b>Phone:</b> <code>{account['phone']}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<code>{s}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <i>Click the code box above to copy instantly. Never share this with anyone!</i>
"""
    buttons = [
        [InlineKeyboardButton(text="🔙 Back to Account", callback_data=f"manage_acc_{acc_id}")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# =========================================================================
# 📱 DEVICE FINGERPRINTS & CLONER
# =========================================================================

@router.callback_query(F.data == "tool_fingerprints")
async def cb_tool_fingerprints(query: CallbackQuery):
    text = """
📱 <b>DEVICE FINGERPRINTS & CLONER SUITE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Telegram server security se safe rehne ke liye aap custom device fingerprint use kar sakte hain. 

Har session in authentic hardware signatures ke sath connect hota hai:

Select any hardware profile to inspect or generate:
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
        [InlineKeyboardButton(text=f"⚡ Generate Session with {fp['name'][:18]}", callback_data=f"fpgen_{dev_key}", style="primary")],
        [InlineKeyboardButton(text="🔙 Back to Devices", callback_data="tool_fingerprints", style="default")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main", style="default")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# =========================================================================
# 📅 CHECK ACCOUNT REGISTRATION AGE
# =========================================================================

@router.callback_query(F.data == "tool_check_age")
async def cb_tool_check_age(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_age_session)
    text = """
📅 <b>CHECK TELEGRAM ACCOUNT AGE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Apne Telegram account ka creation period aur account tier pata karein.

Send any of the following:
1️⃣ <b>Telegram User ID</b> (e.g. <code>8721437284</code>)
2️⃣ <b>Pyrogram or Telethon Session String</b>

Send /cancel to abort.
"""
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_age_session)
async def process_age_session(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    val = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass
    await state.clear()

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
# 🔀 SESSION FORMAT CONVERTER
# =========================================================================

@router.callback_query(F.data == "tool_converter")
async def cb_tool_converter(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_convert_session)
    text = """
🔀 <b>SESSION FORMAT CONVERTER</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Convert between <b>Pyrogram (v2)</b> and <b>Telethon</b> strings instantly without invalidating your login!

Send your string session to convert:
<i>(Send /cancel to abort)</i>
"""
    await query.message.edit_text(text, reply_markup=cancel_keyboard())

@router.message(ToolStates.waiting_convert_session)
async def process_convert_session(message: Message, state: FSMContext):
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
# 👁️ PRIVACY SETTINGS AUDIT
# =========================================================================

@router.callback_query(F.data == "tool_privacy")
async def cb_tool_privacy(query: CallbackQuery):
    text = """
👁️ <b>ACCOUNT PRIVACY AUDIT</b>

Aap session string paste karna chahte hain ya apne saved vault se select karna chahte hain?
"""
    await query.message.edit_text(text, reply_markup=session_source_keyboard("privacy"))

@router.callback_query(F.data == "src_paste_privacy")
async def cb_paste_privacy(query: CallbackQuery, state: FSMContext):
    await state.set_state(ToolStates.waiting_privacy_session)
    await query.message.edit_text(
        "📝 <b>Send String Session to inspect privacy settings:</b>\n\n"
        "<i>(Your session string will be deleted immediately from chat)</i>\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_keyboard()
    )

@router.message(ToolStates.waiting_privacy_session)
async def process_privacy_session(message: Message, state: FSMContext):
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

@router.callback_query(F.data == "src_vault_privacy")
async def cb_vault_privacy(query: CallbackQuery):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    if not accounts:
        await query.answer("Aapke vault me koi account nahi hai!", show_alert=True)
        return

    buttons = []
    for acc in accounts:
        btn_text = f"👤 {acc['account_name']} ({acc['session_type'].capitalize()})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"selpriv_acc_{acc['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_main")])

    await query.message.edit_text("💼 <b>Select an account from your Vault:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("selpriv_acc_"))
async def cb_selpriv_exec(query: CallbackQuery):
    acc_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    account = await db.get_account(acc_id, user_id)
    if not account:
        await query.answer("Account not found!", show_alert=True)
        return

    prog_msg = await query.message.edit_text("🔍 <i>Fetching Privacy Settings...</i>")
    success, res = await check_account_privacy(account["raw_session"])

    if success:
        text = f"""
👁️ <b>PRIVACY REPORT: {account['account_name']}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📞 <b>Phone Number:</b> {res['phone_privacy']}
🕒 <b>Last Seen & Online:</b> {res['last_seen_privacy']}
🖼️ <b>Profile Photo:</b> {res['photo_privacy']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await prog_msg.edit_text(text, reply_markup=back_to_main_keyboard())
    else:
        await prog_msg.edit_text(f"❌ <b>Failed:</b> <code>{res}</code>", reply_markup=back_to_main_keyboard())

# =========================================================================
# 👤 USER CENTER
# =========================================================================

@router.callback_query(F.data == "tool_user_center")
async def cb_user_center(query: CallbackQuery):
    user = query.from_user
    acc_count = await db.count_user_accounts(user.id)
    text = f"""
✨ <b>ICE BOT • USER CENTER</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Name:</b> {user.first_name}
🆔 <b>Telegram ID:</b> <code>{user.id}</code>
🔗 <b>Username:</b> @{user.username or 'None'}
💼 <b>Accounts in Vault:</b> <code>{acc_count}</code>
🛡️ <b>Security Status:</b> AES-256 Cloud Encrypted
⚡ <b>Tier:</b> Free Unlimited Mode
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await query.message.edit_text(text, reply_markup=user_center_keyboard())

# =========================================================================
# 📥 DOCUMENT / FILE UPLOAD HANDLER (.session / .json / .txt)
# =========================================================================

@router.message(F.document)
async def handle_document_upload(message: Message):
    doc = message.document
    fn = doc.file_name or "file"
    if not (fn.endswith(".session") or fn.endswith(".json") or fn.endswith(".txt")):
        await message.reply("⚠️ Please send a <code>.session</code>, <code>.json</code>, or <code>.txt</code> file.", reply_markup=back_to_main_keyboard())
        return

    status_msg = await message.reply("📥 <i>Downloading and parsing file...</i>")
    try:
        file_obj = await message.bot.get_file(doc.file_id)
        stream = await message.bot.download_file(file_obj.file_path)
        content = stream.read().decode("utf-8", errors="ignore").strip()

        if len(content) > 100:
            stype = detect_session_type(content)
            health = await check_session_health(content, stype)
            if health.get("status") == "alive":
                await db.save_account(
                    user_id=message.from_user.id,
                    session_type=stype,
                    account_name=health.get("name") or fn,
                    phone=health.get("phone") or "File Account",
                    tg_user_id=health.get("user_id") or 0,
                    raw_session=content
                )
                await status_msg.edit_text(
                    f"🎉 <b>FILE PARSED & SAVED TO VAULT!</b>\n\n"
                    f"📁 <b>Filename:</b> <code>{fn}</code>\n"
                    f"👤 <b>Name:</b> {health['name']}\n"
                    f"📞 <b>Phone:</b> <code>{health['phone']}</code>\n"
                    f"⚡ <b>Engine:</b> <code>{stype.upper()}</code>",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💼 Open Vault", callback_data="menu_vault")]])
                )
            else:
                await status_msg.edit_text(f"❌ <b>Session in file is dead/invalid:</b> <code>{health.get('error')}</code>", reply_markup=back_to_main_keyboard())
        else:
            await status_msg.edit_text("❌ File does not contain a valid session string.", reply_markup=back_to_main_keyboard())
    except Exception as e:
        await status_msg.edit_text(f"❌ Error processing file: <code>{e}</code>", reply_markup=back_to_main_keyboard())



