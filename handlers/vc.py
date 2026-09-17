import os
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

import config
from database.db import db
import client_manager
from helpers.keyboard import (
    vc_dashboard_keyboard, account_toggle_switch_keyboard, detected_vcs_keyboard,
    vc_delay_keyboard, live_vc_blaster_keyboard, cancel_keyboard, back_to_main_keyboard
)
from helpers.states import VCStates

logger = logging.getLogger("VCHandler")
router = Router()

MEDIA_DIR = config.DATA_DIR / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

async def show_vc_dashboard(target, user_id: int, is_callback: bool = True):
    """Render Voice Chat (VC) Auto-DM Control Dashboard."""
    await db.add_user(user_id)
    user_data = await db.get_user(user_id)
    total_vc_sent = await db.count_vc_dms_sent(user_id)

    vc_msg = (user_data.get("vc_message") or db.DEFAULT_VC_MESSAGE if hasattr(db, "DEFAULT_VC_MESSAGE") else "Custom VC Message").strip()
    vc_type = (user_data.get("vc_msg_type") or "text").upper()
    vc_delay = user_data.get("vc_delay", 2.5)

    text = f"""
╔══════════════════════════╗
║  🎙️ <b>𝗩𝗢𝗜𝗖𝗘 𝗖𝗛𝗔𝗧 𝗔𝗨𝗧𝗢-𝗗𝗠 𝗦𝗨𝗜𝗧𝗘</b> ║
╚══════════════════════════╝
<blockquote><i>Jab bhi aap kisi VC me join hon ya conduct karein, bot live listeners ko automatic custom DM deliver karega!</i></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Current Custom Message:</b>
• <b>Type:</b> <code>{vc_type}</code>
• <b>Preview:</b> <i>{vc_msg[:80]}...</i>

⏱️ <b>Anti-Ban Delay:</b> <code>{vc_delay}s</code> per DM
📊 <b>Total VC DMs Sent:</b> <code>{total_vc_sent}</code>
🛡️ <b>Host Protection:</b> <i>Hosts & Speakers auto-filtered (0 spam)</i>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 <i>Tags: <code>{{name}}</code>, <code>{{channel}}</code>, <code>{{username}}</code></i>
"""
    keyboard = vc_dashboard_keyboard(user_data)
    if is_callback:
        try:
            await target.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest:
            pass
    else:
        await target.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.in_(["menu_vc", "btn_vc_menu"]))
async def cb_menu_vc(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_vc_dashboard(query.message, query.from_user.id, is_callback=True)
    await query.answer()

@router.callback_query(F.data == "vc_toggle_auto")
async def cb_vc_toggle_auto(query: CallbackQuery):
    user_id = query.from_user.id
    new_state = await db.toggle_vc_auto_send(user_id)
    state_txt = "🟢 Real-Time Auto-DM ON ho gaya!" if new_state else "🔴 Real-Time Auto-DM PAUSED ho gaya!"
    await query.answer(state_txt, show_alert=False)
    await show_vc_dashboard(query.message, user_id, is_callback=True)

@router.callback_query(F.data == "vc_select_accounts")
async def cb_vc_select_accounts(query: CallbackQuery):
    user_id = query.from_user.id
    accounts = await db.get_user_accounts(user_id)
    text = """
🎛️ <b>VC Sender Accounts Selector (1-Click ON/OFF)</b>

Aap yahan se customize kar sakte hain ki <b>Voice Chat me kis ID se message jana chahiye aur kis ID se nahi:</b>

• 🟢 <b>[ON]</b> = Is account se DM send hoga & VC join karega.
• 🔴 <b>[OFF]</b> = Ye account completely pause rahega (koi DM nahi jayega).

👇 <i>Neeche kisi bhi account par tap karke instant ON / OFF karein:</i>
"""
    try:
        await query.message.edit_text(text, reply_markup=account_toggle_switch_keyboard(accounts))
    except TelegramBadRequest:
        pass
    await query.answer()

@router.callback_query(F.data.startswith("acc_quick_toggle_"))
async def cb_acc_quick_toggle(query: CallbackQuery):
    user_id = query.from_user.id
    db_id_str = query.data.replace("acc_quick_toggle_", "")
    if db_id_str.isdigit():
        db_id = int(db_id_str)
        new_state = await db.toggle_account_active(db_id, user_id)
        if new_state is False:
            await client_manager.disconnect_client(db_id)
            await query.answer("🔴 Account PAUSED (OFF)!", show_alert=False)
        else:
            await query.answer("🟢 Account ACTIVE (ON)!", show_alert=False)

    accounts = await db.get_user_accounts(user_id)
    try:
        await query.message.edit_reply_markup(reply_markup=account_toggle_switch_keyboard(accounts))
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.in_(["acc_toggle_all_1", "acc_toggle_all_0"]))
async def cb_acc_toggle_all(query: CallbackQuery):
    user_id = query.from_user.id
    target_state = 1 if query.data == "acc_toggle_all_1" else 0
    await db.toggle_all_accounts(user_id, target_state)

    if target_state == 0:
        accounts = await db.get_user_accounts(user_id)
        for a in accounts:
            await client_manager.disconnect_client(a["id"])
        await query.answer("🔴 Sabhi accounts PAUSE (OFF) ho gaye!", show_alert=False)
    else:
        await query.answer("🟢 Sabhi accounts ACTIVE (ON) ho gaye!", show_alert=False)

    accounts = await db.get_user_accounts(user_id)
    try:
        await query.message.edit_reply_markup(reply_markup=account_toggle_switch_keyboard(accounts))
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "vc_auto_detect")
async def cb_vc_auto_detect(query: CallbackQuery):
    user_id = query.from_user.id
    accounts_count = await db.count_user_accounts(user_id)
    if accounts_count == 0:
        await query.answer("⚠️ Pehle koi account login karein!", show_alert=True)
        return

    await query.answer("🔍 Scanning all groups for active Voice Chats...")
    try:
        await query.message.edit_text("🔍 <b>Scanning all groups of your accounts for active Live Voice Chats (VCs)...</b>\n\n<i>Kripya 2-3 seconds intezar karein...</i>")
    except TelegramBadRequest:
        pass

    active_vcs = await client_manager.fetch_user_active_vcs(user_id)
    vcs_count = len(active_vcs)

    text = f"""
🎙️ <b>Auto-Detected Live Voice Chats (VCs)</b>

📊 <b>Found Active VCs:</b> <code>{vcs_count}</code>

👉 <i>Kisi bhi group par click karein. Aapke <b>saare accounts turant us VC ko join kar lenge</b> aur sabhi listeners ko automatic DM deliver ho jayega!</i> 👇
"""
    try:
        await query.message.edit_text(text, reply_markup=detected_vcs_keyboard(active_vcs))
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.startswith("vc_blast_target_"))
async def cb_vc_blast_target(query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.data.replace("vc_blast_target_", "")
    status_msg = await query.message.edit_text("⏳ <b>[1/4] Connecting All Sessions & Joining Voice Chat...</b>\n\n<i>Kripya thoda intezar karein...</i>")

    async def update_live_status(new_status_text: str):
        try:
            await status_msg.edit_text(new_status_text, reply_markup=live_vc_blaster_keyboard())
        except Exception:
            pass

    res = await client_manager.blast_vc_multi_session(user_id, chat_id, status_updater_coro=update_live_status)

    if not res.get("success"):
        error_msg = res.get("error", "Unknown error")
        buttons = [
            [InlineKeyboardButton(text="🔄 Auto-Detect Again", callback_data="vc_auto_detect", style="primary")],
            [InlineKeyboardButton(text="🔙 VC Menu", callback_data="menu_vc", style="default")]
        ]
        await status_msg.edit_text(f"❌ <b>VC Blast Error:</b>\n\n<code>{error_msg}</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        client_manager.start_continuous_vc_blast(user_id, chat_id, status_updater_coro=update_live_status)

        session_lines = []
        for s_rep in res.get("session_reports", []):
            prem_icon = "⭐ [Premium]" if s_rep.get("is_premium") else "📱"
            session_lines.append(
                f"• {prem_icon} <code>{s_rep.get('phone')}</code> ➔ Sent: <code>{s_rep.get('sent')}</code> / Assigned: <code>{s_rep.get('assigned')}</code>"
            )
        breakdown_str = "\n".join(session_lines) if session_lines else "• None"

        summary_text = f"""
🔴 <b>Voice Chat (VC) Real-Time Live Blaster (ACTIVE)</b>

• 🎙️ <b>Group/Channel:</b> <code>{res['chat_title']}</code>
• 👥 <b>Total VC Listeners:</b> <code>{res['total_in_vc']}</code>
• 🛡️ <b>Host/Speakers Filtered:</b> <code>{res.get('skipped_hosts_or_speakers', 0)}</code> (0 msgs to host)
• 🎯 <b>Eligible Unique Users:</b> <code>{res.get('eligible_count', 0)}</code>
• ✅ <b>Delivered in Cycle 1:</b> <code>{res['total_sent']}</code> Users
• 🚫 <b>Skipped (Already Sent):</b> <code>{res['skipped_duplicates']}</code>
• 🛡️ <b>Privacy Restricted:</b> <code>{res['failed_privacy']}</code>
• 👥 <b>Active Sessions Used:</b> <code>{res['sessions_used']}</code>

📊 <b>Session-wise DM Distribution:</b>
{breakdown_str}

⚡ <i>Live Watcher Background me ACTIVE hai! Jaise hi koi naya member VC join karega, use turant DM chala jayega.</i>
"""
        await status_msg.edit_text(summary_text, reply_markup=live_vc_blaster_keyboard())

@router.callback_query(F.data == "vc_stop_blast")
async def cb_vc_stop_blast(query: CallbackQuery):
    user_id = query.from_user.id
    stopped = client_manager.stop_continuous_vc_blast(user_id)
    if stopped:
        await query.answer("⏹️ VC Blast Stop ho gaya!", show_alert=True)
        text = """
⏹️ <b>Voice Chat (VC) Real-Time Blast STOPPED!</b>

• Sabhi sessions ne DM dispatching rok di hai.
• Naya blast start karne ke liye VC Dashboard me jayein.
"""
        buttons = [
            [InlineKeyboardButton(text="🚀 Start New VC Blast", callback_data="vc_send_blast", style="success")],
            [InlineKeyboardButton(text="🎙️ VC Dashboard", callback_data="menu_vc", style="primary")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main", style="default")]
        ]
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        except TelegramBadRequest:
            pass
    else:
        await query.answer("⚠️ Koi active VC blast nahi chal raha.", show_alert=False)

@router.callback_query(F.data == "vc_edit_msg")
async def cb_vc_edit_msg(query: CallbackQuery, state: FSMContext):
    await state.set_state(VCStates.waiting_vc_msg)
    text = """
✍️ <b>Edit Voice Chat (VC) Custom Message</b>

👉 Apna custom message chat me bhejein:
• 📝 <b>Text Message</b> (Supported tags: <code>{name}</code>, <code>{username}</code>, <code>{channel}</code>)
• 🎤 <b>Voice Note</b> (Audio recording)
• 🎭 <b>Telegram Premium Sticker</b>
• 🖼️ <b>Photo / Video</b> with Caption
• 📹 <b>Round Video Note</b>

💡 <i>Jab bhi VC chalegi, participants ko yehi message deliver hoga!</i>
"""
    try:
        await query.message.edit_text(text, reply_markup=cancel_keyboard())
    except TelegramBadRequest:
        pass
    await query.answer()

@router.message(VCStates.waiting_vc_msg)
async def process_vc_msg(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    user_id = message.from_user.id
    status_msg = await message.answer("⏳ Processing & saving custom VC message...")

    try:
        if message.sticker:
            sticker = message.sticker
            s_file = await bot.get_file(sticker.file_id)
            ext = ".tgs" if sticker.is_animated else (".webm" if sticker.is_video else ".webp")
            save_path = str(MEDIA_DIR / f"vc_sticker_{user_id}{ext}")
            await bot.download_file(s_file.file_path, save_path)
            await db.update_vc_message(user_id, sticker.emoji or "🎭 Custom Sticker", "sticker", save_path)

        elif message.photo:
            photo = message.photo[-1]
            p_file = await bot.get_file(photo.file_id)
            save_path = str(MEDIA_DIR / f"vc_photo_{user_id}.jpg")
            await bot.download_file(p_file.file_path, save_path)
            caption = message.caption or ""
            await db.update_vc_message(user_id, caption, "photo", save_path)

        elif message.video:
            video = message.video
            v_file = await bot.get_file(video.file_id)
            save_path = str(MEDIA_DIR / f"vc_video_{user_id}.mp4")
            await bot.download_file(v_file.file_path, save_path)
            caption = message.caption or ""
            await db.update_vc_message(user_id, caption, "video", save_path)

        elif message.voice:
            voice = message.voice
            v_file = await bot.get_file(voice.file_id)
            save_path = str(MEDIA_DIR / f"vc_voice_{user_id}.ogg")
            await bot.download_file(v_file.file_path, save_path)
            caption = message.caption or ""
            await db.update_vc_message(user_id, caption, "voice", save_path)

        elif message.video_note:
            vnote = message.video_note
            vn_file = await bot.get_file(vnote.file_id)
            save_path = str(MEDIA_DIR / f"vc_vnote_{user_id}.mp4")
            await bot.download_file(vn_file.file_path, save_path)
            await db.update_vc_message(user_id, "📹 Round Video Note", "video_note", save_path)

        elif message.text:
            await db.update_vc_message(user_id, message.text, "text", None)

        await state.clear()
        await status_msg.edit_text("🎉 <b>VC Custom Message Successfully Saved!</b>\n\nNeeche dashboard se preview aur blast test karein 👇")
        await show_vc_dashboard(message, user_id, is_callback=False)

    except Exception as e:
        logger.error(f"Error saving VC message: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ <b>Error saving message:</b> <code>{e}</code>")

@router.callback_query(F.data == "vc_send_blast")
async def cb_vc_send_blast(query: CallbackQuery, state: FSMContext):
    user_id = query.from_user.id
    accounts_count = await db.count_user_accounts(user_id)
    if accounts_count == 0:
        await query.answer("⚠️ Pehle koi account login karein!", show_alert=True)
        return

    await state.set_state(VCStates.waiting_vc_chat)
    text = """
🚀 <b>Send DM Blast to VC Participants (Manual Link)</b>

👉 Jis Group/Channel me <b>Voice Chat (VC) chal rahi hai</b>, uska <b>Username</b> ya <b>Link</b> ya <b>ID</b> bhejein:

<i>(Examples: <code>@mygroup</code> ya <code>https://t.me/mygroup</code> ya <code>-1001234567890</code>)</i>

💡 <i>Tip: Aap '🔍 Auto-Detect Live VCs' se bina link copy kiye direct 1-click select bhi kar sakte hain!</i>
"""
    try:
        await query.message.edit_text(text, reply_markup=cancel_keyboard())
    except TelegramBadRequest:
        pass
    await query.answer()

@router.message(VCStates.waiting_vc_chat)
async def process_vc_chat(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.reply("Cancelled.", reply_markup=back_to_main_keyboard())
        return

    chat_input = message.text.strip()
    user_id = message.from_user.id
    await state.clear()

    status_msg = await message.answer("⏳ <b>[1/4] Connecting All Sessions & Joining Voice Chat...</b>\n\n<i>Kripya thoda intezar karein...</i>")

    async def update_live_status(new_status_text: str):
        try:
            await status_msg.edit_text(new_status_text, reply_markup=live_vc_blaster_keyboard())
        except Exception:
            pass

    res = await client_manager.blast_vc_multi_session(user_id, chat_input, status_updater_coro=update_live_status)

    if not res.get("success"):
        error_msg = res.get("error", "Unknown error")
        buttons = [
            [InlineKeyboardButton(text="🔄 Retry with Another Group", callback_data="vc_send_blast", style="primary")],
            [InlineKeyboardButton(text="🔙 VC Menu", callback_data="menu_vc", style="default")]
        ]
        await status_msg.edit_text(f"❌ <b>VC Blast Error:</b>\n\n<code>{error_msg}</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        client_manager.start_continuous_vc_blast(user_id, chat_input, status_updater_coro=update_live_status)

        session_lines = []
        for s_rep in res.get("session_reports", []):
            prem_icon = "⭐ [Premium]" if s_rep.get("is_premium") else "📱"
            session_lines.append(
                f"• {prem_icon} <code>{s_rep.get('phone')}</code> ➔ Sent: <code>{s_rep.get('sent')}</code> / Assigned: <code>{s_rep.get('assigned')}</code>"
            )
        breakdown_str = "\n".join(session_lines) if session_lines else "• None"

        summary_text = f"""
🔴 <b>Voice Chat (VC) Real-Time Live Blaster (ACTIVE)</b>

• 🎙️ <b>Group/Channel:</b> <code>{res['chat_title']}</code>
• 👥 <b>Total VC Listeners:</b> <code>{res['total_in_vc']}</code>
• 🛡️ <b>Host/Speakers Filtered:</b> <code>{res.get('skipped_hosts_or_speakers', 0)}</code> (0 msgs to host)
• 🎯 <b>Eligible Unique Users:</b> <code>{res.get('eligible_count', 0)}</code>
• ✅ <b>Delivered in Cycle 1:</b> <code>{res['total_sent']}</code> Users
• 🚫 <b>Skipped (Already Sent):</b> <code>{res['skipped_duplicates']}</code>
• 🛡️ <b>Privacy Restricted:</b> <code>{res['failed_privacy']}</code>
• 👥 <b>Active Sessions Used:</b> <code>{res['sessions_used']}</code>

📊 <b>Session-wise DM Distribution:</b>
{breakdown_str}

⚡ <i>Live Watcher Background me ACTIVE hai! Jaise hi koi naya member VC join karega, use turant DM chala jayega.</i>
"""
        await status_msg.edit_text(summary_text, reply_markup=live_vc_blaster_keyboard())

@router.callback_query(F.data == "vc_delay_menu")
async def cb_vc_delay_menu(query: CallbackQuery):
    text = """
⏱️ <b>Voice Chat Anti-Ban Delay Settings</b>

DMs bhejne ke beech kitna second ka delay rakhna chahte hain taaki account safe rahe?
"""
    try:
        await query.message.edit_text(text, reply_markup=vc_delay_keyboard())
    except TelegramBadRequest:
        pass
    await query.answer()

@router.callback_query(F.data.startswith("vc_set_delay_"))
async def cb_vc_set_delay(query: CallbackQuery):
    user_id = query.from_user.id
    delay_val = float(query.data.replace("vc_set_delay_", ""))
    await db.update_vc_delay(user_id, delay_val)
    await query.answer(f"⏱️ Delay updated to {delay_val}s!", show_alert=False)
    await show_vc_dashboard(query.message, user_id, is_callback=True)

@router.callback_query(F.data == "vc_reset_msg")
async def cb_vc_reset_msg(query: CallbackQuery):
    user_id = query.from_user.id
    await db.update_vc_message(user_id, db.DEFAULT_VC_MESSAGE if hasattr(db, "DEFAULT_VC_MESSAGE") else "Custom Message", "text", None)
    await query.answer("✅ VC message default par reset ho gaya!", show_alert=True)
    await show_vc_dashboard(query.message, user_id, is_callback=True)

@router.callback_query(F.data == "vc_stats")
async def cb_vc_stats(query: CallbackQuery):
    user_id = query.from_user.id
    total_sent = await db.count_vc_dms_sent(user_id)
    await query.answer(f"📊 Total VC DMs Delivered: {total_sent}", show_alert=True)
