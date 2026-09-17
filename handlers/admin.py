import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import config
from database.db import db
from helpers.keyboard import cancel_keyboard, back_to_main_keyboard
from helpers.states import AdminStates

router = Router()

@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(query: CallbackQuery):
    if query.from_user.id != config.OWNER_ID:
        await query.answer("Access Denied ❌", show_alert=True)
        return

    users_count = await db.get_users_count()
    text = f"""
👑 <b>ADMIN CONTROL PANEL</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 <b>Total Bot Users:</b> <code>{users_count}</code>
🤖 <b>Bot ID:</b> <code>{config.BOT_TOKEN.split(':')[0]}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    buttons = [
        [InlineKeyboardButton(text="📢 ʙʀᴏᴀᴅᴄᴀsᴛ ᴍᴇssᴀɢᴇ", callback_data="admin_broadcast", icon_custom_emoji_id="5445284980978621387")],
        [InlineKeyboardButton(text="🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_main", icon_custom_emoji_id="5465665476988315663")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(query: CallbackQuery, state: FSMContext):
    if query.from_user.id != config.OWNER_ID:
        return
    await state.set_state(AdminStates.waiting_broadcast_msg)
    await query.message.edit_text(
        "📢 <b>Enter the message you want to broadcast to all users:</b>\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_keyboard()
    )

@router.message(AdminStates.waiting_broadcast_msg)
async def process_broadcast(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return
    await state.clear()

    status_msg = await message.reply("🔄 <i>Broadcasting in progress...</i>")
    user_ids = await db.get_all_users()

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await message.copy_to(chat_id=uid)
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

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != config.OWNER_ID:
        return
    count = await db.get_users_count()
    await message.reply(f"📊 <b>Total Users:</b> <code>{count}</code>")
