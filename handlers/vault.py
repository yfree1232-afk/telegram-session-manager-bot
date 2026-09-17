import io
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile
)
from database.db import db
from helpers.keyboard import cancel_keyboard, back_to_main_keyboard, account_detail_keyboard
from helpers.states import VaultStates
from helpers.session_tools import check_session_health
from handlers.common import detect_session_type

router = Router()

@router.callback_query(F.data == "menu_vault")
async def cb_menu_vault(query: CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)

    text = """
╭━━━━━━━━━━━━━━━━━━━━╮
│  💼 <b>ᴍʏ ᴀᴄᴄᴏᴜɴᴛ ᴠᴀᴜʟᴛ</b>  │
╰━━━━━━━━━━━━━━━━━━━━╯
<i>Aapke sabhi sessions AES-Fernet encrypted form me secure hain.</i>

"""
    if not accounts:
        text += "📭 <i>Aapke vault me abhi koi account save nahi hai.</i>"
    else:
        text += f"📊 <b>Total Accounts Saved:</b> <code>{len(accounts)}</code>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for idx, acc in enumerate(accounts, start=1):
            text += f"<b>{idx}.</b> {acc['account_name']} (<code>{acc['phone'] or 'N/A'}</code>) — <b>{acc['session_type'].upper()}</b>\n"

    buttons = []
    if accounts:
        for acc in accounts:
            btn_text = f"👤 {acc['account_name']} ({acc['session_type'].capitalize()})"
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"manage_acc_{acc['id']}")])

    buttons.append([
        InlineKeyboardButton(text="➕ ᴀᴅᴅ ᴀᴄᴄᴏᴜɴᴛ", callback_data="vault_add_acc"),
        InlineKeyboardButton(text="🔍 ᴄʜᴇᴄᴋ ᴀʟʟ ʜᴇᴀʟᴛʜ", callback_data="vault_check_all")
    ])
    if accounts:
        buttons.append([InlineKeyboardButton(text="📤 ᴇxᴘᴏʀᴛ ᴠᴀᴜʟᴛ (ʙᴀᴄᴋᴜᴘ)", callback_data="vault_export")])
    buttons.append([InlineKeyboardButton(text="🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_main")])

    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("manage_acc_"))
async def cb_manage_acc(query: CallbackQuery):
    acc_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    acc = await db.get_account(acc_id, user_id)
    if not acc:
        await query.answer("Account not found!", show_alert=True)
        return

    text = f"""
👤 <b>Account Card: {acc['account_name']}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📞 <b>Phone:</b> <code>{acc['phone'] or 'N/A'}</code>
🆔 <b>User ID:</b> <code>{acc['tg_user_id'] or 'N/A'}</code>
⚡ <b>Type:</b> <code>{acc['session_type'].upper()}</code>
📅 <b>Added On:</b> <code>{acc['created_at'][:10]}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await query.message.edit_text(text, reply_markup=account_detail_keyboard(acc_id))

@router.callback_query(F.data.startswith("check_acc_status_"))
async def cb_check_status(query: CallbackQuery):
    acc_id = int(query.data.split("_")[3])
    user_id = query.from_user.id
    acc = await db.get_account(acc_id, user_id)
    if not acc:
        await query.answer("Account not found!", show_alert=True)
        return

    await query.answer("Checking status...", show_alert=False)
    status_msg = await query.message.reply("🔄 <i>Testing session connectivity...</i>")

    info = await check_session_health(acc["raw_session"], acc["session_type"])
    if info["status"] == "alive":
        res_text = f"""
🟢 <b>ACCOUNT IS ALIVE & HEALTHY!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Name:</b> {info['name']}
🆔 <b>User ID:</b> <code>{info['user_id']}</code>
📞 <b>Phone:</b> <code>{info['phone']}</code>
🌐 <b>DC ID:</b> {info['dc_id']}
💎 <b>Premium:</b> {'Yes ⭐️' if info['is_premium'] else 'No'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    else:
        res_text = f"""
🔴 <b>ACCOUNT IS DEAD / INACTIVE!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>Reason:</b> <code>{info['error']}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>Tip: Ye session Telegram server se revoke ya delete ho chuka hai.</i>
"""
    await status_msg.edit_text(res_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Account", callback_data=f"manage_acc_{acc_id}")]]))

@router.callback_query(F.data.startswith("del_acc_confirm_"))
async def cb_del_confirm(query: CallbackQuery):
    acc_id = int(query.data.split("_")[3])
    buttons = [
        [
            InlineKeyboardButton(text="🗑️ ʏᴇs, ᴅᴇʟᴇᴛᴇ", callback_data=f"del_acc_exec_{acc_id}"),
            InlineKeyboardButton(text="❌ ᴄᴀɴᴄᴇʟ", callback_data=f"manage_acc_{acc_id}")
        ]
    ]
    await query.message.edit_text("⚠️ <b>Are you sure you want to remove this account from your Vault?</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("del_acc_exec_"))
async def cb_del_exec(query: CallbackQuery):
    acc_id = int(query.data.split("_")[3])
    user_id = query.from_user.id
    await db.delete_account(acc_id, user_id)
    await query.answer("Account removed from vault 🗑️", show_alert=True)
    await cb_menu_vault(query, None)

@router.callback_query(F.data == "vault_add_acc")
async def cb_vault_add_acc(query: CallbackQuery, state: FSMContext):
    await state.set_state(VaultStates.waiting_session)
    await query.message.edit_text(
        "📝 <b>Send the String Session you want to save:</b>\n\n"
        "<i>(Supports both Pyrogram v2 & Telethon string sessions)</i>\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_keyboard()
    )

@router.message(VaultStates.waiting_session)
async def process_vault_add(message: Message, state: FSMContext):
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

    verif_msg = await message.answer("🔄 <i>Verifying session...</i>")
    stype = detect_session_type(raw_session)
    health = await check_session_health(raw_session, stype)

    if health["status"] != "alive":
        await verif_msg.edit_text(
            f"❌ <b>Invalid or Dead Session!</b>\n\nError: <code>{health['error']}</code>",
            reply_markup=back_to_main_keyboard()
        )
        return

    acc_name = health["name"] or "Telegram Account"
    await db.save_account(
        user_id=message.from_user.id,
        session_type=stype,
        account_name=acc_name,
        phone=health["phone"],
        tg_user_id=health["user_id"],
        raw_session=raw_session
    )
    await verif_msg.edit_text(
        f"🎉 <b>ACCOUNT SAVED TO VAULT!</b>\n\n"
        f"👤 <b>Name:</b> {acc_name}\n"
        f"📞 <b>Phone:</b> <code>{health['phone']}</code>\n"
        f"⚡ <b>Engine:</b> <code>{stype.upper()}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💼 Open Vault", callback_data="menu_vault")]])
    )

@router.callback_query(F.data == "vault_check_all")
async def cb_vault_check_all(query: CallbackQuery):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    if not accounts:
        await query.answer("No accounts in vault!", show_alert=True)
        return

    await query.answer("Checking health...", show_alert=False)
    progress_msg = await query.message.edit_text(f"⏳ <i>Checking {len(accounts)} accounts... Please wait.</i>")

    report = "📊 <b>VAULT HEALTH REPORT</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    alive_cnt = 0
    dead_cnt = 0

    for idx, acc in enumerate(accounts, start=1):
        full_acc = await db.get_account(acc["id"], user_id)
        health = await check_session_health(full_acc["raw_session"], full_acc["session_type"])
        if health["status"] == "alive":
            alive_cnt += 1
            report += f"{idx}. 🟢 <b>{acc['account_name']}</b> (<code>{acc['phone'] or 'N/A'}</code>) — <b>ALIVE</b>\n"
        else:
            dead_cnt += 1
            report += f"{idx}. 🔴 <b>{acc['account_name']}</b> — <b>DEAD</b> (<code>{health['error']}</code>)\n"

    report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    report += f"🟢 <b>Alive:</b> {alive_cnt} | 🔴 <b>Dead:</b> {dead_cnt}"

    await progress_msg.edit_text(
        report,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Vault", callback_data="menu_vault")]])
    )

@router.callback_query(F.data == "vault_export")
async def cb_vault_export(query: CallbackQuery):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    if not accounts:
        await query.answer("No accounts to export!", show_alert=True)
        return

    await query.answer("Generating backup file...", show_alert=False)

    buf = io.StringIO()
    buf.write("# SESSION MANAGER VOLTX - VAULT BACKUP\n\n")

    for idx, acc in enumerate(accounts, start=1):
        full_acc = await db.get_account(acc["id"], user_id)
        buf.write(f"[{idx}] Name: {acc['account_name']} | Phone: {acc['phone']} | Type: {acc['session_type'].upper()}\n")
        buf.write(f"Session: {full_acc['raw_session']}\n\n")

    file_bytes = buf.getvalue().encode("utf-8")
    doc = BufferedInputFile(file_bytes, filename=f"vault_backup_{user_id}.txt")

    await query.bot.send_document(
        chat_id=user_id,
        document=doc,
        caption="🔐 <b>Here is your Vault Backup file!</b>\n\n<i>Keep this file completely confidential.</i>"
    )
    await query.message.reply("✅ Backup file sent above!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Vault", callback_data="menu_vault")]]))
