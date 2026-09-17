from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db
from helpers.keyboard import (
    tools_menu_keyboard, session_source_keyboard, cancel_keyboard, back_to_main_keyboard
)
from helpers.states import ToolStates
from helpers.session_tools import leave_all_dialogs, check_session_health
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
