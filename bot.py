import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PasswordHashInvalidError,
    PhoneNumberBannedError,
    PhoneNumberInvalidError,
    FloodWaitError
)

from config import BOT_TOKEN, API_ID, API_HASH, ADMIN_IDS
import database
import session_manager
import custom_tasks

logger = logging.getLogger("Bot")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

auth_clients: dict[int, dict] = {}

class LoginStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_otp = State()
    waiting_for_2fa = State()
    waiting_for_session_string = State()
    waiting_for_channel_link = State()
    waiting_for_message_link = State()
    waiting_for_forward_target = State()
    waiting_for_comment_text = State()
    waiting_for_custom_emoji = State()
    waiting_for_custom_report = State()
    waiting_for_zip_file = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def get_main_menu_keyboard(is_user_admin: bool = False) -> InlineKeyboardMarkup:
    if is_user_admin:
        buttons = [
            [
                InlineKeyboardButton(text="📢 Global Channel Join (ALL DB Accs 🚀)", callback_data="admin_global_join", style="success"),
                InlineKeyboardButton(text="🎯 Global Post Multi-Tool 🔥", callback_data="admin_global_post", style="primary")
            ],
            [
                InlineKeyboardButton(text="👑 Global Sessions Hub (All Users)", callback_data="admin_global_hub", style="primary"),
                InlineKeyboardButton(text="🔍 Global Health Check All", callback_data="admin_global_health", style="primary")
            ],
            [
                InlineKeyboardButton(text="📦 Batch Import (ZIP / Files 📁)", callback_data="act_import_zip", style="success"),
                InlineKeyboardButton(text="➕ Add New Session", callback_data="menu_add_session", style="success")
            ],
            [
                InlineKeyboardButton(text="📱 My Personal Sessions", callback_data="hub_sessions"),
                InlineKeyboardButton(text="📊 Master DB Stats", callback_data="hub_stats")
            ],
            [
                InlineKeyboardButton(text="ℹ️ Help & Guide", callback_data="hub_help")
            ]
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton(text="📢 Join Channel (My Accounts 🚀)", callback_data="act_join_channel", style="success"),
                InlineKeyboardButton(text="🎯 Post Multi-Tool (My Accounts ⚡)", callback_data="act_post_toolkit", style="primary")
            ],
            [
                InlineKeyboardButton(text="📦 Batch Import (ZIP / Files 📁)", callback_data="act_import_zip", style="success"),
                InlineKeyboardButton(text="➕ Add Single Session", callback_data="menu_add_session", style="success")
            ],
            [
                InlineKeyboardButton(text="📱 My Connected Sessions", callback_data="hub_sessions"),
                InlineKeyboardButton(text="🔍 Health Check (My Accounts)", callback_data="act_health_all", style="primary")
            ],
            [
                InlineKeyboardButton(text="📊 Database Stats", callback_data="hub_stats"),
                InlineKeyboardButton(text="ℹ️ Help & Guide", callback_data="hub_help")
            ]
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_add_session_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Phone Number (OTP Login)", callback_data="add_phone_otp", style="primary")],
        [InlineKeyboardButton(text="🔑 Paste String Session (1-Click)", callback_data="add_string_session", style="success")],
        [InlineKeyboardButton(text="📦 Upload ZIP / .Session Files", callback_data="act_import_zip", style="success")],
        [InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="menu_main")]
    ])

def build_sessions_list_keyboard(sessions: list[dict], is_global_view: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if not sessions:
        buttons.append([InlineKeyboardButton(text="⚠️ Koi Session Add Nahi Hai", callback_data="noop")])
    else:
        if not is_global_view:
            buttons.append([
                InlineKeyboardButton(text="📢 Join Channel", callback_data="act_join_channel", style="success"),
                InlineKeyboardButton(text="🎯 Post Multi-Tool", callback_data="act_post_toolkit", style="primary")
            ])
        for s in sessions[:60]:
            acc_id = s["account_id"]
            owner = s.get("owner_id", "")
            phone = s.get("phone_number") or f"ID:{acc_id}"
            name = s.get("first_name") or "Account"
            is_active = bool(s.get("is_active", 1))
            status_icon = "🟢" if is_active else "🔴"
            btn_style = "success" if is_active else "danger"
            if is_global_view:
                btn_text = f"{status_icon} {name} ({phone}) [U:{owner}]"
            else:
                btn_text = f"{status_icon} {name} ({phone})"
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"view_sess_{owner}_{acc_id}" if is_global_view else f"view_sess_{acc_id}", style=btn_style)])

    if not is_global_view:
        buttons.append([
            InlineKeyboardButton(text="➕ Add Account", callback_data="menu_add_session", style="primary"),
            InlineKeyboardButton(text="📦 Import ZIP", callback_data="act_import_zip", style="success"),
            InlineKeyboardButton(text="🔄 Refresh", callback_data="hub_sessions")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="🔄 Refresh Global Pool", callback_data="admin_global_hub", style="primary")
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="menu_main")] )
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_single_session_keyboard(session: dict) -> InlineKeyboardMarkup:
    owner_id = session.get("owner_id")
    acc_id = session["account_id"]
    is_active = bool(session.get("is_active", 1))
    toggle_text = "⏸️ Deactivate / Pause" if is_active else "▶️ Activate Session"
    toggle_style = "danger" if is_active else "success"
    
    cb_suffix = f"{owner_id}_{acc_id}" if owner_id else str(acc_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=f"tog_sess_{cb_suffix}", style=toggle_style)],
        [
            InlineKeyboardButton(text="🔍 Test Health", callback_data=f"chk_sess_{cb_suffix}", style="primary"),
            InlineKeyboardButton(text="🗑️ Delete Account", callback_data=f"del_sess_{cb_suffix}", style="danger")
        ],
        [InlineKeyboardButton(text="🔙 Back to Sessions List", callback_data="hub_sessions")]
    ])

def build_post_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ React with Emojis", callback_data="post_menu_react", style="primary"),
            InlineKeyboardButton(text="🔄 Forward Post", callback_data="post_menu_forward", style="primary")
        ],
        [
            InlineKeyboardButton(text="⚠️ Report Post", callback_data="post_menu_report", style="danger"),
            InlineKeyboardButton(text="📋 Copy Text & Link", callback_data="post_menu_copy")
        ],
        [
            InlineKeyboardButton(text="💬 Post Comment / Reply", callback_data="post_menu_comment", style="success")
        ],
        [
            InlineKeyboardButton(text="🔄 Select Another Post", callback_data="act_post_toolkit"),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")
        ]
    ])

def build_reactions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍", callback_data="react_👍", style="success"),
            InlineKeyboardButton(text="❤️", callback_data="react_❤️", style="danger"),
            InlineKeyboardButton(text="🔥", callback_data="react_🔥", style="primary"),
            InlineKeyboardButton(text="👏", callback_data="react_👏", style="success")
        ],
        [
            InlineKeyboardButton(text="🎉", callback_data="react_🎉", style="primary"),
            InlineKeyboardButton(text="🤩", callback_data="react_🤩", style="primary"),
            InlineKeyboardButton(text="🚀", callback_data="react_🚀", style="success"),
            InlineKeyboardButton(text="😍", callback_data="react_😍", style="danger")
        ],
        [
            InlineKeyboardButton(text="😱", callback_data="react_😱"),
            InlineKeyboardButton(text="😂", callback_data="react_😂", style="primary"),
            InlineKeyboardButton(text="👎", callback_data="react_👎", style="danger"),
            InlineKeyboardButton(text="💩", callback_data="react_💩")
        ],
        [
            InlineKeyboardButton(text="✍️ Custom Emoji Input", callback_data="post_custom_react", style="primary")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to Post Actions", callback_data="post_back_actions")
        ]
    ])

def build_report_reasons_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚫 Spam", callback_data="rep_spam", style="danger"),
            InlineKeyboardButton(text="🎭 Fake / Scam", callback_data="rep_fake", style="danger")
        ],
        [
            InlineKeyboardButton(text="🔞 Pornography", callback_data="rep_pornography", style="danger"),
            InlineKeyboardButton(text="🩸 Violence", callback_data="rep_violence", style="danger")
        ],
        [
            InlineKeyboardButton(text="⚠️ Copyright", callback_data="rep_copyright", style="danger"),
            InlineKeyboardButton(text="🔞 Child Abuse", callback_data="rep_child_abuse", style="danger")
        ],
        [
            InlineKeyboardButton(text="📝 Other (Custom Reason)", callback_data="post_custom_report")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to Post Actions", callback_data="post_back_actions")
        ]
    ])

@dp.message(F.text.startswith("/start") | F.text.startswith("/menu"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    admin_mode = is_admin(user_id)

    sessions = await database.get_user_sessions(user_id)
    active_count = sum(1 for s in sessions if s.get("is_active", 1))

    if admin_mode:
        global_sessions = await database.get_all_stored_sessions()
        global_active = sum(1 for s in global_sessions if s.get("is_active", 1))
        stats = await database.get_stats()
        text = (
            f"👑 **ADMIN MASTER CONTROL DASHBOARD**\n\n"
            f"👋 Welcome Master `{message.from_user.first_name}`!\n\n"
            f"• 🌐 **Total Global Sessions (All Users):** `{len(global_sessions)}`\n"
            f"• 🟢 **Active Global Accounts:** `{global_active}`\n"
            f"• 👥 **Total Registered Users:** `{stats.get('total_users')}`\n"
            f"• 📱 **Your Personal Sessions:** `{len(sessions)}`\n"
            f"• 💾 **Database Engine:** `{database.DB_ENGINE.upper()}`\n\n"
            f"Aap pure database ke sabhi accounts par actions execute kar sakte hain 👇"
        )
    else:
        text = (
            f"👋 **Namaste {message.from_user.first_name}!**\n\n"
            f"🚀 **Telegram Multi-Session Manager Dashboard**\n\n"
            f"• 📱 **My Connected Sessions:** `{len(sessions)}`\n"
            f"• 🟢 **Active Accounts:** `{active_count}`\n"
            f"• 💾 **Database Engine:** `{database.DB_ENGINE.upper()}`\n\n"
            f"Neeche diye gaye buttons se apne sessions manage karein ya naya account add karein 👇"
        )
    await message.answer(text, reply_markup=get_main_menu_keyboard(admin_mode))

@dp.message(F.text.startswith("/help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    admin_note = "\n👑 **Admin Mode Active:** Aapko pure database ke sabhi accounts ka master control mila hua hai." if is_admin(user_id) else ""
    text = (
        f"📖 **Telegram Session Manager Bot - User Guide**{admin_note}\n\n"
        "1. 📦 **ZIP Session Import:** Koi bhi `.zip` file jisme `.session` files hon, direct chat me bhejein! Bot unhe extract karke connect karega.\n"
        "2. 📢 **Bulk Channel Join:** Public `@username` ya private `https://t.me/+...` link bhej kar sabhi active accounts se join karwayein.\n"
        "3. 🎯 **Post Multi-Tool:** Post ka link (`https://t.me/channel/123`) bhejein aur sabhi accounts se **Reactions**, **Forwarding**, **Reporting**, **Text/Link Copy**, ya **Comments** run karein!\n"
        "4. 📱 **Phone / String Login:** Manual 1-by-1 Phone OTP ya String Session add karein.\n"
        "5. 🔍 **Health Check:** Real-time ping test run karke check karein koi account revoked ya flood-wait toh nahi hua."
    )
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="menu_main")]
    ]))

@dp.callback_query()
async def callback_router(query: types.CallbackQuery, state: FSMContext):
    user_id = query.from_user.id
    data = query.data
    admin_mode = is_admin(user_id)
    logger.info(f"🔘 User {user_id} (Admin: {admin_mode}) clicked: '{data}'")

    try:
        if data == "menu_main":
            await state.clear()
            sessions = await database.get_user_sessions(user_id)
            active_count = sum(1 for s in sessions if s.get("is_active", 1))
            
            if admin_mode:
                global_sessions = await database.get_all_stored_sessions()
                global_active = sum(1 for s in global_sessions if s.get("is_active", 1))
                stats = await database.get_stats()
                text = (
                    f"👑 **ADMIN MASTER CONTROL DASHBOARD**\n\n"
                    f"• 🌐 **Total Global Sessions:** `{len(global_sessions)}`\n"
                    f"• 🟢 **Active Global Accounts:** `{global_active}`\n"
                    f"• 👥 **Total Users:** `{stats.get('total_users')}`\n"
                    f"• 📱 **Your Sessions:** `{len(sessions)}`\n"
                    f"• 💾 **Database Engine:** `{database.DB_ENGINE.upper()}`\n\n"
                    f"Options select karein 👇"
                )
            else:
                text = (
                    f"🏠 **Main Control Dashboard**\n\n"
                    f"• 📱 **My Sessions:** `{len(sessions)}`\n"
                    f"• 🟢 **Active Accounts:** `{active_count}`\n"
                    f"• 💾 **Database Engine:** `{database.DB_ENGINE.upper()}`\n\n"
                    f"Options select karein 👇"
                )
            try:
                await query.message.edit_text(text, reply_markup=get_main_menu_keyboard(admin_mode))
            except TelegramBadRequest:
                pass
            await query.answer()

        # ----------------- Admin Global Actions -----------------
        elif data == "admin_global_hub":
            if not admin_mode:
                await query.answer("⛔ Admin access required!", show_alert=True)
                return
            all_sessions = await database.get_all_stored_sessions()
            active_count = sum(1 for s in all_sessions if s.get("is_active", 1))
            text = (
                f"👑 **Global Sessions Database ({len(all_sessions)} Total | {active_count} Active)**\n\n"
                f"Sabhi users ke connected Telegram accounts neeche listed hain. Kisi bhi account par tap karke manage karein:"
            )
            try:
                await query.message.edit_text(text, reply_markup=build_sessions_list_keyboard(all_sessions, is_global_view=True))
            except TelegramBadRequest:
                pass
            await query.answer()

        elif data == "admin_global_health":
            if not admin_mode:
                await query.answer("⛔ Admin access required!", show_alert=True)
                return
            await query.answer("🔍 Checking all global accounts...", show_alert=False)
            all_sessions = await database.get_all_stored_sessions()
            if not all_sessions:
                await query.message.answer("⚠️ Pure database me koi session nahi hai.")
                return
            
            report = [f"📊 **Global Health Check Report ({len(all_sessions)} Accounts):**\n"]
            for s in all_sessions:
                owner = s["owner_id"]
                acc_id = s["account_id"]
                phone = s.get("phone_number", str(acc_id))
                name = s.get("first_name", "Account")
                res = await session_manager.check_session_health(owner, acc_id)
                if res.get("status") == "HEALTHY":
                    report.append(f"• 🟢 `{name}` ({phone}) [U:{owner}] ➔ **Online**")
                else:
                    report.append(f"• 🔴 `{name}` ({phone}) [U:{owner}] ➔ **{res.get('message')}**")
                await asyncio.sleep(0.2)

            await query.message.answer("\n".join(report))

        elif data == "admin_global_join":
            if not admin_mode:
                await query.answer("⛔ Admin access required!", show_alert=True)
                return
            all_sessions = await database.get_all_active_sessions()
            if not all_sessions:
                await query.answer("⚠️ Database me koi active session nahi mila!", show_alert=True)
                return
            await state.set_state(LoginStates.waiting_for_channel_link)
            await state.update_data({"is_global": True})
            text = (
                f"📢 **GLOBAL Bulk Channel Joiner (ALL Accounts in DB 🚀)**\n\n"
                f"👑 Pure database ke **{len(all_sessions)} active accounts** is channel ko join karenge.\n\n"
                f"👉 **Kripya Channel / Group Link ya Username bhejein:**\n\n"
                f"• Public: `https://t.me/mychannel` ya `@mychannel`\n"
                f"• Private: `https://t.me/+AbCdEfGh`\n\n"
                f"*(💡 Anti-Flood protection: 1.5s delay per account)*"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]])
            try:
                await query.message.edit_text(text, reply_markup=kb)
            except TelegramBadRequest:
                pass
            await query.answer()

        elif data == "admin_global_post":
            if not admin_mode:
                await query.answer("⛔ Admin access required!", show_alert=True)
                return
            all_sessions = await database.get_all_active_sessions()
            if not all_sessions:
                await query.answer("⚠️ Database me koi active session nahi mila!", show_alert=True)
                return
            await state.set_state(LoginStates.waiting_for_message_link)
            await state.update_data({"is_global": True})
            text = (
                f"🎯 **GLOBAL Channel Post Multi-Tool (ALL Accounts in DB 🔥)**\n\n"
                f"👑 Pure database ke **{len(all_sessions)} accounts** se Actions (Reactions, Report, Forward, Comments) lene ke liye **Post Link** bhejein:\n\n"
                f"👉 **Example:** `https://t.me/mychannel/1234` ya `https://t.me/c/1234567890/567`"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]])
            try:
                await query.message.edit_text(text, reply_markup=kb)
            except TelegramBadRequest:
                pass
            await query.answer()

        # ----------------- Bulk Channel Joiner -----------------
        elif data == "act_join_channel":
            sessions = await database.get_user_sessions(user_id)
            active_sessions = [s for s in sessions if s.get("is_active", 1)]
            
            if not active_sessions:
                await query.answer("⚠️ Pehle kam se kam 1 active session add karein!", show_alert=True)
                return

            await state.set_state(LoginStates.waiting_for_channel_link)
            text = (
                f"📢 **Bulk Channel / Group Joiner**\n\n"
                f"Aapke **{len(active_sessions)} active accounts** is channel ko join karenge.\n\n"
                f"👉 **Kripya Channel / Group ka Link ya Username yahan chat me bhejein:**\n\n"
                f"• 🌐 **Public Link / Username:** `https://t.me/mychannel` ya `@mychannel`\n"
                f"• 🔒 **Private Invite Link:** `https://t.me/+AbCdEfGhIjK` ya `+AbCdEfGhIjK`\n\n"
                f"*(💡 Anti-Flood protection ke liye har account ke beech 1.5s ka delay lagaya jayega)*"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]
            ])
            try:
                await query.message.edit_text(text, reply_markup=kb)
            except TelegramBadRequest:
                pass
            await query.answer()

        # ----------------- ZIP Batch Import Info -----------------
        elif data == "act_import_zip":
            await state.set_state(LoginStates.waiting_for_zip_file)
            text = (
                "📦 **Batch Session Import (ZIP / File Upload)**\n\n"
                "Aap direct multiple accounts ek sath import kar sakte hain:\n\n"
                "• 🗂️ **ZIP File:** Ek `.zip` file bhejein jisme multiple `.session` files hon.\n"
                "• 📄 **`.session` File:** Single Telethon SQLite session file direct bhejein.\n"
                "• 📝 **`.txt` File:** Pyrogram/Telethon string sessions ki text file (har line par ek session).\n\n"
                "👉 **Bas apni file yahan chat me attach / upload karke bhejein!**"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]])
            try:
                await query.message.edit_text(text, reply_markup=kb)
            except TelegramBadRequest:
                pass
            await query.answer()

        # ----------------- Post Multi-Tool Entry -----------------
        elif data == "act_post_toolkit":
            sessions = await database.get_user_sessions(user_id)
            active_sessions = [s for s in sessions if s.get("is_active", 1)]
            
            if not active_sessions:
                await query.answer("⚠️ Pehle kam se kam 1 active session add karein!", show_alert=True)
                return

            await state.set_state(LoginStates.waiting_for_message_link)
            text = (
                "🎯 **Channel Post / Message Multi-Tool**\n\n"
                "Kisi bhi channel ya group ke message par actions lene ke liye uska **Message Link** bhejein:\n\n"
                "👉 **Examples:**\n"
                "• `https://t.me/mychannel/1234` (Public Channel Post)\n"
                "• `https://t.me/c/1234567890/567` (Private Channel Post)\n"
                "• `@mychannel 1234` (Username & Post ID)\n\n"
                "*(💡 Iske baad aap Reactions, Forward, Report, Text Copy, Comments sab kuch perform kar sakenge)*"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]])
            try:
                await query.message.edit_text(text, reply_markup=kb)
            except TelegramBadRequest:
                pass
            await query.answer()

        # Post Actions: Return to Post Dashboard
        elif data == "post_back_actions":
            state_data = await state.get_data()
            if not state_data.get("peer"):
                await query.answer("Session expired, kripya message link dobara bhejein.", show_alert=True)
                return
            
            title = state_data.get("title", "Target Post")
            msg_id = state_data.get("msg_id")
            views = state_data.get("views", 0)
            forwards = state_data.get("forwards", 0)
            snippet = state_data.get("snippet", "")
            
            text = (
                f"🎯 **Post Selected:** `{title}` (Post #{msg_id})\n\n"
                f"• 👁️ **Views:** `{views}` | 🔄 **Forwards:** `{forwards}`\n"
                f"• 📝 **Snippet:** {snippet}\n\n"
                f"👇 **Neeche diye gaye action me se select karein:**"
            )
            try:
                await query.message.edit_text(text, reply_markup=build_post_actions_keyboard())
            except TelegramBadRequest:
                pass
            await query.answer()

        # Post Action 1: React Menu
        elif data == "post_menu_react":
            state_data = await state.get_data()
            title = state_data.get("title", "Target Post")
            msg_id = state_data.get("msg_id")
            text = (
                f"❤️ **Select Reaction Emoji for Post #{msg_id}** (`{title}`):\n\n"
                f"Kisi bhi emoji par tap karein, sabhi active accounts turant ye reaction post par denge:"
            )
            try:
                await query.message.edit_text(text, reply_markup=build_reactions_keyboard())
            except TelegramBadRequest:
                pass
            await query.answer()

        # Trigger Reaction
        elif data.startswith("react_"):
            emoji = data.replace("react_", "")
            state_data = await state.get_data()
            peer = state_data.get("peer")
            msg_id = state_data.get("msg_id")
            is_glob = state_data.get("is_global", False) and admin_mode

            if not peer or not msg_id:
                await query.answer("Post selection expired!", show_alert=True)
                return

            if is_glob:
                target_sessions = await database.get_all_active_sessions()
            else:
                user_sess = await database.get_user_sessions(user_id)
                target_sessions = [s for s in user_sess if s.get("is_active", 1)]

            status_msg = await query.message.answer(f"⏳ **Reacting with {emoji} across {len(target_sessions)} accounts...**")
            rep = [f"❤️ **Emoji Reaction Report ({emoji})**\n"]
            success_cnt = 0

            for s in target_sessions:
                s_owner = s["owner_id"]
                acc_id = s["account_id"]
                phone = s.get("phone_number", str(acc_id))
                name = s.get("first_name", "Account")
                client = session_manager.get_client(s_owner, acc_id)
                if not client or not client.is_connected():
                    if s.get("session_string"):
                        await session_manager.start_session(s_owner, acc_id, s["session_string"])
                        client = session_manager.get_client(s_owner, acc_id)

                if client and client.is_connected():
                    r = await session_manager.react_to_message_single_session(client, peer, msg_id, emoji)
                    rep.append(f"• {r.get('icon', '🔹')} **{name}** (`{phone}`): {r.get('note')}")
                    if r.get("status") == "SUCCESS":
                        success_cnt += 1
                else:
                    rep.append(f"• 🔴 **{name}** (`{phone}`): Offline")
                await asyncio.sleep(1.0)

            rep.append(f"\n📊 **Result:** `{success_cnt} / {len(target_sessions)}` Reacted Successfully!")
            await status_msg.edit_text("\n".join(rep), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Post Actions", callback_data="post_back_actions")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
            ]))
            await query.answer()

        # Post Action 2: Custom Emoji React State
        elif data == "post_custom_react":
            await state.set_state(LoginStates.waiting_for_custom_emoji)
            await query.message.answer(
                "✍️ **Custom Reaction Emoji Bhejein:**\n\nChat me koi bhi single emoji bhejein (jaise: 🔥, 💎, 👑, etc.):",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="post_back_actions")]])
            )
            await query.answer()

        # Post Action 3: Report Menu
        elif data == "post_menu_report":
            state_data = await state.get_data()
            title = state_data.get("title", "Target Post")
            msg_id = state_data.get("msg_id")
            text = (
                f"⚠️ **Report Post #{msg_id} (`{title}`)**\n\n"
                f"Telegram moderation ko report submit karne ke liye reason select karein:\n"
                f"*(Sabhi active sessions se official report bhej di jayegi)*"
            )
            try:
                await query.message.edit_text(text, reply_markup=build_report_reasons_keyboard())
            except TelegramBadRequest:
                pass
            await query.answer()

        # Trigger Report
        elif data.startswith("rep_"):
            reason_key = data.replace("rep_", "")
            state_data = await state.get_data()
            peer = state_data.get("peer")
            msg_id = state_data.get("msg_id")
            is_glob = state_data.get("is_global", False) and admin_mode

            if not peer or not msg_id:
                await query.answer("Post selection expired!", show_alert=True)
                return

            if is_glob:
                target_sessions = await database.get_all_active_sessions()
            else:
                user_sess = await database.get_user_sessions(user_id)
                target_sessions = [s for s in user_sess if s.get("is_active", 1)]

            status_msg = await query.message.answer(f"⏳ **Filing {reason_key.upper()} reports across {len(target_sessions)} accounts...**")
            rep = [f"⚠️ **Report Filing Report ({reason_key.upper()})**\n"]
            success_cnt = 0

            for s in target_sessions:
                s_owner = s["owner_id"]
                acc_id = s["account_id"]
                phone = s.get("phone_number", str(acc_id))
                name = s.get("first_name", "Account")
                client = session_manager.get_client(s_owner, acc_id)
                if not client or not client.is_connected():
                    if s.get("session_string"):
                        await session_manager.start_session(s_owner, acc_id, s["session_string"])
                        client = session_manager.get_client(s_owner, acc_id)

                if client and client.is_connected():
                    r = await session_manager.report_message_single_session(client, peer, msg_id, reason_key, "Reported inappropriate content")
                    rep.append(f"• {r.get('icon', '🔹')} **{name}** (`{phone}`): {r.get('note')}")
                    if r.get("status") == "SUCCESS":
                        success_cnt += 1
                else:
                    rep.append(f"• 🔴 **{name}** (`{phone}`): Offline")
                await asyncio.sleep(1.0)

            rep.append(f"\n📊 **Result:** `{success_cnt} / {len(target_sessions)}` Reports Submitted!")
            await status_msg.edit_text("\n".join(rep), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Post Actions", callback_data="post_back_actions")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
            ]))
            await query.answer()

        # Post Action 4: Custom Report Reason
        elif data == "post_custom_report":
            await state.set_state(LoginStates.waiting_for_custom_report)
            await query.message.answer(
                "📝 **Custom Report Reason Type Karein:**\n\nKripya apna report message / reason chat me type karke bhejein:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="post_back_actions")]])
            )
            await query.answer()

        # Post Action 5: Forward Menu
        elif data == "post_menu_forward":
            await state.set_state(LoginStates.waiting_for_forward_target)
            await query.message.answer(
                "🔄 **Forward Message Target:**\n\n"
                "Target Channel username, Group username, ya User ID bhejein jahan sabhi accounts is post ko forward karenge:\n"
                "*(Example: `@mybackupchannel` ya `me` for Saved Messages)*",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="post_back_actions")]])
            )
            await query.answer()

        # Post Action 6: Copy Text & Link
        elif data == "post_menu_copy":
            state_data = await state.get_data()
            title = state_data.get("title", "Post")
            full_text = state_data.get("full_text", "[No Text]")
            direct_link = state_data.get("direct_link", "N/A")
            msg_id = state_data.get("msg_id")

            copy_msg = (
                f"📋 **Extracted Post Content (Post #{msg_id} - `{title}`):**\n\n"
                f"🔗 **Direct Link:** `{direct_link}`\n\n"
                f"📝 **Post Text:**\n```\n{full_text}\n```"
            )
            await query.message.answer(copy_msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Post Actions", callback_data="post_back_actions")]
            ]))
            await query.answer("Text & Link Copied!", show_alert=False)

        # Post Action 7: Post Comment
        elif data == "post_menu_comment":
            await state.set_state(LoginStates.waiting_for_comment_text)
            await query.message.answer(
                "💬 **Send Comment / Reply:**\n\n"
                "Apna comment ya message yahan type karke bhejein jo sabhi active accounts is post par send karenge:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="post_back_actions")]])
            )
            await query.answer()

        elif data == "hub_sessions":
            sessions = await database.get_user_sessions(user_id)
            text = (
                f"📱 **My Connected Telegram Sessions ({len(sessions)})**\n\n"
                f"Kisi bhi account par tap karke uski details, health check ya settings open karein:"
            )
            try:
                await query.message.edit_text(text, reply_markup=build_sessions_list_keyboard(sessions))
            except TelegramBadRequest:
                pass
            await query.answer()

        elif data == "menu_add_session":
            text = (
                "➕ **Add Telegram Account / Session**\n\n"
                "Aap kiske through account connect karna chahte hain?\n\n"
                "1. 📱 **Phone Number (OTP):** Bot aapse number aur OTP mangega.\n"
                "2. 🔑 **String Session:** Agar aapke paas Telethon/Pyrogram String Session pehle se hai toh direct paste karein."
            )
            try:
                await query.message.edit_text(text, reply_markup=get_add_session_keyboard())
            except TelegramBadRequest:
                pass
            await query.answer()

        elif data == "add_phone_otp":
            await state.set_state(LoginStates.waiting_for_phone)
            text = (
                "📲 **Telegram Phone (OTP) Login**\n\n"
                "Apna Telegram Phone Number country code ke sath yahan bhejein:\n"
                "*(Example: `+919876543210` ya `+19127418551`)*"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔑 Paste String Session Instead", callback_data="add_string_session")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]
            ])
            try:
                await query.message.edit_text(text, reply_markup=kb)
            except TelegramBadRequest:
                pass
            await query.answer()

        elif data == "add_string_session":
            await state.set_state(LoginStates.waiting_for_session_string)
            text = (
                "🔑 **Direct String Session Import (1-Click)**\n\n"
                "Apna **Telethon ya Pyrogram String Session** yahan chat me paste karke bhejein.\n\n"
                "*(💡 Is method se Telegram ka koi delay warning nahi aata aur session turant active ho jata hai!)*"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]])
            try:
                await query.message.edit_text(text, reply_markup=kb)
            except TelegramBadRequest:
                pass
            await query.answer()

        elif data.startswith("view_sess_"):
            acc_id = int(data.replace("view_sess_", ""))
            sess = await database.get_session(user_id, acc_id)
            if not sess:
                await query.answer("Account not found!", show_alert=True)
                return

            phone = sess.get("phone_number") or "N/A"
            name = f"{sess.get('first_name', '')} {sess.get('last_name', '')}".strip() or "N/A"
            uname = f"@{sess.get('username')}" if sess.get("username") else "None"
            dc = sess.get("dc_id", 0)
            is_active = bool(sess.get("is_active", 1))
            status_txt = "🟢 Active (Online)" if is_active else "🔴 Paused / Inactive"
            note = sess.get("status_note", "OK")

            text = (
                f"👤 **Account Details**\n\n"
                f"• 🏷️ **Name:** `{name}`\n"
                f"• 📱 **Phone:** `{phone}`\n"
                f"• 🆔 **Telegram ID:** `{acc_id}`\n"
                f"• 🌐 **Username:** {uname}\n"
                f"• 🏢 **Data Center:** `DC{dc}`\n"
                f"• 📡 **Status:** {status_txt}\n"
                f"• 📝 **Note:** `{note}`\n"
            )
            try:
                await query.message.edit_text(text, reply_markup=build_single_session_keyboard(sess))
            except TelegramBadRequest:
                pass
            await query.answer()

        elif data.startswith("tog_sess_"):
            acc_id = int(data.replace("tog_sess_", ""))
            new_active = await database.toggle_session_active(user_id, acc_id)
            sess = await database.get_session(user_id, acc_id)
            if new_active:
                if sess and sess.get("session_string"):
                    await session_manager.start_session(user_id, acc_id, sess["session_string"])
                await query.answer("▶️ Session Activated!", show_alert=False)
            else:
                await session_manager.stop_session(user_id, acc_id)
                await query.answer("⏸️ Session Paused!", show_alert=False)

            if sess:
                phone = sess.get("phone_number") or "N/A"
                name = f"{sess.get('first_name', '')} {sess.get('last_name', '')}".strip() or "N/A"
                uname = f"@{sess.get('username')}" if sess.get("username") else "None"
                dc = sess.get("dc_id", 0)
                status_txt = "🟢 Active (Online)" if new_active else "🔴 Paused / Inactive"
                note = sess.get("status_note", "OK")
                text = (
                    f"👤 **Account Details**\n\n"
                    f"• 🏷️ **Name:** `{name}`\n"
                    f"• 📱 **Phone:** `{phone}`\n"
                    f"• 🆔 **Telegram ID:** `{acc_id}`\n"
                    f"• 🌐 **Username:** {uname}\n"
                    f"• 🏢 **Data Center:** `DC{dc}`\n"
                    f"• 📡 **Status:** {status_txt}\n"
                    f"• 📝 **Note:** `{note}`\n"
                )
                try:
                    await query.message.edit_text(text, reply_markup=build_single_session_keyboard(sess))
                except TelegramBadRequest:
                    pass

        elif data.startswith("chk_sess_"):
            acc_id = int(data.replace("chk_sess_", ""))
            await query.answer("⏳ Running health check...", show_alert=False)
            res = await session_manager.check_session_health(user_id, acc_id)
            status_symbol = "✅" if res.get("status") == "HEALTHY" else "❌"
            msg = f"{status_symbol} **Health Result:** {res.get('status')}\n\nDetails: `{res.get('message')}`"
            await query.message.answer(msg)

        elif data.startswith("del_sess_"):
            acc_id = int(data.replace("del_sess_", ""))
            await session_manager.stop_session(user_id, acc_id)
            await database.delete_session(user_id, acc_id)
            await query.answer("🗑️ Session deleted successfully!", show_alert=True)
            
            sessions = await database.get_user_sessions(user_id)
            text = (
                f"📱 **My Connected Telegram Sessions ({len(sessions)})**\n\n"
                f"Session delete ho chuka hai. Naya account add karne ke liye niche tap karein:"
            )
            try:
                await query.message.edit_text(text, reply_markup=build_sessions_list_keyboard(sessions))
            except TelegramBadRequest:
                pass

        elif data == "act_health_all":
            await query.answer("🔍 Checking all accounts...", show_alert=False)
            sessions = await database.get_user_sessions(user_id)
            if not sessions:
                await query.message.answer("⚠️ Koi session add nahi hai.")
                return
            
            report = ["📊 **Sessions Health Check Report:**\n"]
            for s in sessions:
                acc_id = s["account_id"]
                phone = s.get("phone_number", str(acc_id))
                name = s.get("first_name", "Account")
                res = await session_manager.check_session_health(user_id, acc_id)
                if res.get("status") == "HEALTHY":
                    report.append(f"• 🟢 `{name}` ({phone}) ➔ **Healthy & Online**")
                else:
                    report.append(f"• 🔴 `{name}` ({phone}) ➔ **Issue:** {res.get('message')}")
                await asyncio.sleep(0.2)

            await query.message.answer("\n".join(report))

        elif data == "hub_stats":
            stats = await database.get_stats()
            text = (
                "📊 **Session Manager Global Statistics**\n\n"
                f"• 💾 **Database Engine:** `{stats.get('engine')}`\n"
                f"• 👥 **Total Users:** `{stats.get('total_users')}`\n"
                f"• 📱 **Total Sessions Stored:** `{stats.get('total_sessions')}`\n"
                f"• 🟢 **Active Live Sessions:** `{stats.get('active_sessions')}`\n"
                f"• ⚡ **Memory Pool Active:** `{len(session_manager.active_clients)}`\n"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Main Menu", callback_data="menu_main")]])
            try:
                await query.message.edit_text(text, reply_markup=kb)
            except TelegramBadRequest:
                pass
            await query.answer()

        elif data == "hub_help":
            await cmd_help(query.message)
            await query.answer()

    except Exception as e:
        logger.error(f"Error handling callback {data}: {e}", exc_info=True)
        await query.answer(f"Error: {e}", show_alert=True)

# ----------------- Document / ZIP File Upload Handler -----------------

@dp.message(F.document)
async def handle_document_upload(message: types.Message, state: FSMContext):
    import tempfile, shutil
    user_id = message.from_user.id
    doc = message.document
    fname = doc.file_name or "uploaded_file"
    
    status_msg = await message.answer(f"⏳ **File receive hui:** `{fname}` ({round(doc.file_size/1024, 1)} KB)\n\nProcessing & Extracting sessions...")
    
    temp_dir = tempfile.mkdtemp(prefix="tg_upload_")
    local_file_path = os.path.join(temp_dir, fname)

    try:
        await bot.download(doc, destination=local_file_path)

        # Case 1: ZIP file
        if fname.lower().endswith(".zip"):
            report = await session_manager.import_sessions_from_zip_file(user_id, local_file_path)
            
            lines = [
                f"📦 **ZIP Batch Import Report**",
                f"📁 **File:** `{fname}`",
                f"📊 **Result:** `{report['success']}` Added Successfully | `{report['failed']}` Failed\n"
            ]
            lines.extend(report["details"][:20])
            if len(report["details"]) > 20:
                lines.append(f"• *(and {len(report['details']) - 20} more...)*")

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 View Sessions Hub", callback_data="hub_sessions")],
                [InlineKeyboardButton(text="📢 Join Channel with All", callback_data="act_join_channel")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
            ])
            await status_msg.edit_text("\n".join(lines), reply_markup=kb)

        # Case 2: Single .session SQLite file
        elif fname.lower().endswith(".session"):
            session_str = session_manager.convert_sqlite_session_to_string(local_file_path)
            if not session_str:
                await status_msg.edit_text("❌ `.session` file invalid hai ya decode nahi ho saki.")
                return

            ok, details, err = await session_manager.verify_and_extract_session_details(session_str)
            if ok and details:
                acc_id = details["account_id"]
                phone = details["phone_number"]
                fn = details["first_name"]
                ln = details["last_name"]
                un = details["username"]
                dc = details["dc_id"]

                await database.save_or_update_session(user_id, acc_id, phone, session_str, fn, ln, un, dc)
                await session_manager.start_session(user_id, acc_id, session_str)

                full_name = f"{fn} {ln}".strip() or "User"
                await status_msg.edit_text(
                    f"🎉 **`.session` File Imported Successfully!**\n\n"
                    f"• 👤 **Name:** `{full_name}`\n"
                    f"• 📱 **Phone:** `{phone}`\n"
                    f"• 🆔 **ID:** `{acc_id}`\n"
                    f"• 🏢 **DC:** `DC{dc}`\n\n"
                    f"Session active pool me register ho chuki hai!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📱 View Sessions", callback_data="hub_sessions")],
                        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
                    ])
                )
            else:
                await status_msg.edit_text(f"❌ Session Verification Failed: `{err}`")

        # Case 3: Text file with multiple string sessions
        elif fname.lower().endswith((".txt", ".str", ".json")):
            with open(local_file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [l.strip() for l in f.read().splitlines() if len(l.strip()) > 40 and not l.strip().startswith("#")]

            if not lines:
                await status_msg.edit_text("❌ File me koi valid session string nahi mili.")
                return

            success_cnt = 0
            fail_cnt = 0
            rep_lines = [f"📄 **Text File Import ({len(lines)} Strings found)**\n"]

            for s_str in lines:
                ok, details, err = await session_manager.verify_and_extract_session_details(s_str)
                if ok and details:
                    acc_id = details["account_id"]
                    phone = details["phone_number"]
                    fn = details["first_name"]
                    ln = details["last_name"]
                    un = details["username"]
                    dc = details["dc_id"]

                    await database.save_or_update_session(user_id, acc_id, phone, s_str, fn, ln, un, dc)
                    await session_manager.start_session(user_id, acc_id, s_str)
                    success_cnt += 1
                    rep_lines.append(f"• 🟢 `{phone}` ({fn}) Connected ✅")
                else:
                    fail_cnt += 1
                    rep_lines.append(f"• 🔴 String invalid: {err or 'Auth fail'}")
                await asyncio.sleep(0.3)

            rep_lines.append(f"\n📊 **Summary:** `{success_cnt}` Added / `{fail_cnt}` Failed")
            await status_msg.edit_text("\n".join(rep_lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 View Sessions", callback_data="hub_sessions")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
            ]))

        else:
            await status_msg.edit_text("⚠️ Kripya `.zip`, `.session`, ya `.txt` file upload karein.")

    except Exception as e:
        logger.error(f"Error handling document upload: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Error processing file: `{e}`")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

# ----------------- Post Multi-Tool Handlers -----------------

# 1. Message Link Input for Post Multi-Tool
@dp.message(LoginStates.waiting_for_message_link)
async def handle_message_link_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    raw_link = (message.text or "").strip()
    admin_mode = is_admin(user_id)
    state_data = await state.get_data()
    is_glob = state_data.get("is_global", False) and admin_mode
    
    peer, msg_id = session_manager.parse_message_link(raw_link)
    if not peer or not msg_id:
        await message.answer(
            "❌ **Invalid Message Link!**\n\n"
            "Format: `https://t.me/mychannel/123` ya `https://t.me/c/1234567890/123`",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]])
        )
        return

    if is_glob:
        target_sessions = await database.get_all_active_sessions()
    else:
        user_sess = await database.get_user_sessions(user_id)
        target_sessions = [s for s in user_sess if s.get("is_active", 1)]

    if not target_sessions:
        await state.clear()
        await message.answer("⚠️ Koi active session nahi mila.", reply_markup=get_main_menu_keyboard(admin_mode))
        return

    status_msg = await message.answer("⏳ Post details fetch ho rahi hain...")
    
    first_sess = target_sessions[0]
    s_owner = first_sess["owner_id"]
    s_acc = first_sess["account_id"]
    client = session_manager.get_client(s_owner, s_acc)
    if not client or not client.is_connected():
        if first_sess.get("session_string"):
            await session_manager.start_session(s_owner, s_acc, first_sess["session_string"])
            client = session_manager.get_client(s_owner, s_acc)

    if not client or not client.is_connected():
        await status_msg.edit_text("❌ Client connect nahi ho saka.")
        return

    preview = await session_manager.fetch_message_preview(client, peer, msg_id)
    if not preview.get("found"):
        await status_msg.edit_text(f"❌ Message Fetch Failed: `{preview.get('error')}`")
        return

    raw_text = preview["text"]
    snippet = raw_text[:120] + ("..." if len(raw_text) > 120 else "")
    scope_txt = "👑 GLOBAL (ALL ACCOUNTS)" if is_glob else "📱 MY ACCOUNTS"
    
    await state.update_data({
        "peer": peer,
        "msg_id": msg_id,
        "title": preview["title"],
        "views": preview["views"],
        "forwards": preview["forwards"],
        "full_text": raw_text,
        "direct_link": preview["direct_link"],
        "snippet": snippet,
        "is_global": is_glob
    })

    text = (
        f"🎯 **Post Selected ({scope_txt}):** `{preview['title']}` (Post #{msg_id})\n\n"
        f"• 👁️ **Views:** `{preview['views']}` | 🔄 **Forwards:** `{preview['forwards']}`\n"
        f"• 📝 **Text Preview:** {snippet}\n\n"
        f"👇 **Neeche diye gaye buttons se action select karein:**"
    )
    await status_msg.edit_text(text, reply_markup=build_post_actions_keyboard())

# 2. Custom Emoji Reaction Input
@dp.message(LoginStates.waiting_for_custom_emoji)
async def handle_custom_emoji_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    emoji = message.text.strip()
    admin_mode = is_admin(user_id)
    
    state_data = await state.get_data()
    peer = state_data.get("peer")
    msg_id = state_data.get("msg_id")
    is_glob = state_data.get("is_global", False) and admin_mode

    if not peer or not msg_id:
        await state.clear()
        await message.answer("⚠️ Session expired.", reply_markup=get_main_menu_keyboard(admin_mode))
        return

    if is_glob:
        target_sessions = await database.get_all_active_sessions()
    else:
        user_sess = await database.get_user_sessions(user_id)
        target_sessions = [s for s in user_sess if s.get("is_active", 1)]

    status_msg = await message.answer(f"⏳ **Reacting with {emoji} across {len(target_sessions)} accounts...**")
    rep = [f"❤️ **Custom Emoji Reaction Report ({emoji})**\n"]
    success_cnt = 0

    for s in target_sessions:
        s_owner = s["owner_id"]
        acc_id = s["account_id"]
        phone = s.get("phone_number", str(acc_id))
        name = s.get("first_name", "Account")
        client = session_manager.get_client(s_owner, acc_id)
        if not client or not client.is_connected():
            if s.get("session_string"):
                await session_manager.start_session(s_owner, acc_id, s["session_string"])
                client = session_manager.get_client(s_owner, acc_id)

        if client and client.is_connected():
            r = await session_manager.react_to_message_single_session(client, peer, msg_id, emoji)
            rep.append(f"• {r.get('icon', '🔹')} **{name}** (`{phone}`): {r.get('note')}")
            if r.get("status") == "SUCCESS":
                success_cnt += 1
        else:
            rep.append(f"• 🔴 **{name}** (`{phone}`): Offline")
        await asyncio.sleep(1.0)

    rep.append(f"\n📊 **Result:** `{success_cnt} / {len(target_sessions)}` Reacted Successfully!")
    await status_msg.edit_text("\n".join(rep), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Post Actions", callback_data="post_back_actions")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
    ]))

# 3. Custom Report Reason Input
@dp.message(LoginStates.waiting_for_custom_report)
async def handle_custom_report_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    custom_reason = message.text.strip()
    admin_mode = is_admin(user_id)
    
    state_data = await state.get_data()
    peer = state_data.get("peer")
    msg_id = state_data.get("msg_id")
    is_glob = state_data.get("is_global", False) and admin_mode

    if not peer or not msg_id:
        await state.clear()
        await message.answer("⚠️ Session expired.", reply_markup=get_main_menu_keyboard(admin_mode))
        return

    if is_glob:
        target_sessions = await database.get_all_active_sessions()
    else:
        user_sess = await database.get_user_sessions(user_id)
        target_sessions = [s for s in user_sess if s.get("is_active", 1)]

    status_msg = await message.answer(f"⏳ **Filing custom reports across {len(target_sessions)} accounts...**")
    rep = [f"⚠️ **Custom Report Filing Report**\n"]
    success_cnt = 0

    for s in target_sessions:
        s_owner = s["owner_id"]
        acc_id = s["account_id"]
        phone = s.get("phone_number", str(acc_id))
        name = s.get("first_name", "Account")
        client = session_manager.get_client(s_owner, acc_id)
        if not client or not client.is_connected():
            if s.get("session_string"):
                await session_manager.start_session(s_owner, acc_id, s["session_string"])
                client = session_manager.get_client(s_owner, acc_id)

        if client and client.is_connected():
            r = await session_manager.report_message_single_session(client, peer, msg_id, "other", custom_reason)
            rep.append(f"• {r.get('icon', '🔹')} **{name}** (`{phone}`): {r.get('note')}")
            if r.get("status") == "SUCCESS":
                success_cnt += 1
        else:
            rep.append(f"• 🔴 **{name}** (`{phone}`): Offline")
        await asyncio.sleep(1.0)

    rep.append(f"\n📊 **Result:** `{success_cnt} / {len(target_sessions)}` Reports Submitted!")
    await status_msg.edit_text("\n".join(rep), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Post Actions", callback_data="post_back_actions")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
    ]))

# 4. Forward Target Input
@dp.message(LoginStates.waiting_for_forward_target)
async def handle_forward_target_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    target_dest = message.text.strip()
    admin_mode = is_admin(user_id)
    
    state_data = await state.get_data()
    from_peer = state_data.get("peer")
    msg_id = state_data.get("msg_id")
    is_glob = state_data.get("is_global", False) and admin_mode

    if not from_peer or not msg_id:
        await state.clear()
        await message.answer("⚠️ Session expired.", reply_markup=get_main_menu_keyboard(admin_mode))
        return

    if is_glob:
        target_sessions = await database.get_all_active_sessions()
    else:
        user_sess = await database.get_user_sessions(user_id)
        target_sessions = [s for s in user_sess if s.get("is_active", 1)]

    status_msg = await message.answer(f"⏳ **Forwarding post across {len(target_sessions)} accounts to `{target_dest}`...**")
    rep = [f"🔄 **Forwarding Summary (To: `{target_dest}`)**\n"]
    success_cnt = 0

    for s in target_sessions:
        s_owner = s["owner_id"]
        acc_id = s["account_id"]
        phone = s.get("phone_number", str(acc_id))
        name = s.get("first_name", "Account")
        client = session_manager.get_client(s_owner, acc_id)
        if not client or not client.is_connected():
            if s.get("session_string"):
                await session_manager.start_session(s_owner, acc_id, s["session_string"])
                client = session_manager.get_client(s_owner, acc_id)

        if client and client.is_connected():
            r = await session_manager.forward_message_single_session(client, from_peer, msg_id, target_dest)
            rep.append(f"• {r.get('icon', '🔹')} **{name}** (`{phone}`): {r.get('note')}")
            if r.get("status") == "SUCCESS":
                success_cnt += 1
        else:
            rep.append(f"• 🔴 **{name}** (`{phone}`): Offline")
        await asyncio.sleep(1.0)

    rep.append(f"\n📊 **Result:** `{success_cnt} / {len(target_sessions)}` Forwarded Successfully!")
    await status_msg.edit_text("\n".join(rep), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Post Actions", callback_data="post_back_actions")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
    ]))

# 5. Comment / Reply Text Input
@dp.message(LoginStates.waiting_for_comment_text)
async def handle_comment_text_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    comment_text = message.text.strip()
    admin_mode = is_admin(user_id)
    
    state_data = await state.get_data()
    peer = state_data.get("peer")
    msg_id = state_data.get("msg_id")
    is_glob = state_data.get("is_global", False) and admin_mode

    if not peer:
        await state.clear()
        await message.answer("⚠️ Session expired.", reply_markup=get_main_menu_keyboard(admin_mode))
        return

    if is_glob:
        target_sessions = await database.get_all_active_sessions()
    else:
        user_sess = await database.get_user_sessions(user_id)
        target_sessions = [s for s in user_sess if s.get("is_active", 1)]

    status_msg = await message.answer(f"⏳ **Posting comment across {len(target_sessions)} accounts...**")
    rep = [f"💬 **Comment Posting Summary**\n"]
    success_cnt = 0

    for s in target_sessions:
        s_owner = s["owner_id"]
        acc_id = s["account_id"]
        phone = s.get("phone_number", str(acc_id))
        name = s.get("first_name", "Account")
        client = session_manager.get_client(s_owner, acc_id)
        if not client or not client.is_connected():
            if s.get("session_string"):
                await session_manager.start_session(s_owner, acc_id, s["session_string"])
                client = session_manager.get_client(s_owner, acc_id)

        if client and client.is_connected():
            r = await session_manager.send_comment_single_session(client, peer, msg_id, comment_text)
            rep.append(f"• {r.get('icon', '🔹')} **{name}** (`{phone}`): {r.get('note')}")
            if r.get("status") == "SUCCESS":
                success_cnt += 1
        else:
            rep.append(f"• 🔴 **{name}** (`{phone}`): Offline")
        await asyncio.sleep(1.0)

    rep.append(f"\n📊 **Result:** `{success_cnt} / {len(target_sessions)}` Comments Posted!")
    await status_msg.edit_text("\n".join(rep), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Post Actions", callback_data="post_back_actions")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
    ]))

# 6. Bulk Channel Join Message Handler
@dp.message(LoginStates.waiting_for_channel_link)
async def handle_channel_link_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    raw_link = (message.text or "").strip()
    admin_mode = is_admin(user_id)
    
    if not raw_link:
        await message.answer("⚠️ Kripya valid channel link ya username bhejein.")
        return

    state_data = await state.get_data()
    is_glob = state_data.get("is_global", False) and admin_mode

    if is_glob:
        active_sessions = await database.get_all_active_sessions()
    else:
        user_sess = await database.get_user_sessions(user_id)
        active_sessions = [s for s in user_sess if s.get("is_active", 1)]

    if not active_sessions:
        await state.clear()
        await message.answer("⚠️ Koi active session nahi mila.", reply_markup=get_main_menu_keyboard(admin_mode))
        return

    await state.clear()
    scope_txt = "👑 GLOBAL (ALL DB ACCOUNTS)" if is_glob else "📱 MY ACCOUNTS"
    status_msg = await message.answer(f"⏳ **Joining in progress across {len(active_sessions)} accounts ({scope_txt})...**\n\nTarget: `{raw_link}`")

    report_lines = [
        f"📢 **Bulk Channel Join Summary ({scope_txt})**",
        f"🔗 **Target:** `{raw_link}`\n"
    ]
    
    success_count = 0
    fail_count = 0

    for idx, s in enumerate(active_sessions, 1):
        s_owner = s["owner_id"]
        acc_id = s["account_id"]
        phone = s.get("phone_number") or str(acc_id)
        name = s.get("first_name") or "Account"
        session_str = s.get("session_string")

        client = session_manager.get_client(s_owner, acc_id)
        if not client or not client.is_connected():
            if session_str:
                await session_manager.start_session(s_owner, acc_id, session_str)
                client = session_manager.get_client(s_owner, acc_id)

        if not client or not client.is_connected():
            report_lines.append(f"• 🔴 **{name}** (`{phone}`): Offline / Auth Failed")
            fail_count += 1
            continue

        res = await session_manager.join_channel_single_session(client, raw_link)
        icon = res.get("icon", "🔹")
        note = res.get("note", "")
        
        if res.get("status") in ("SUCCESS", "ALREADY_MEMBER", "REQUEST_SENT"):
            success_count += 1
        else:
            fail_count += 1

        report_lines.append(f"• {icon} **{name}** (`{phone}`): {note}")
        
        if idx < len(active_sessions):
            await asyncio.sleep(1.5)

    report_lines.append(f"\n━━━━━━━━━━━━━━━━━━━")
    report_lines.append(f"📊 **Result:** `{success_count}` Processed / `{fail_count}` Failed (Total: `{len(active_sessions)}`)")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Join Another Channel", callback_data="admin_global_join" if is_glob else "act_join_channel")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
    ])

    await status_msg.edit_text("\n".join(report_lines), reply_markup=kb)

# ----------------- Interactive Login Flow Handlers -----------------

@dp.message(LoginStates.waiting_for_session_string)
async def handle_string_session_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    session_str = (message.text or "").strip()
    
    if not session_str:
        await message.answer("⚠️ Kripya valid string session text paste karein.")
        return

    status_msg = await message.answer("⏳ Session verify ki ja rahi hai...")
    ok, details, err = await session_manager.verify_and_extract_session_details(session_str)
    
    if not ok or not details:
        await status_msg.edit_text(
            f"❌ **Invalid Session String!**\n\nError: `{err}`\n\nKripya valid Telethon/Pyrogram session string paste karein.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Retry", callback_data="add_string_session")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]
            ])
        )
        return

    acc_id = details["account_id"]
    phone = details["phone_number"]
    fn = details["first_name"]
    ln = details["last_name"]
    un = details["username"]
    dc = details["dc_id"]

    await database.save_or_update_session(user_id, acc_id, phone, session_str, fn, ln, un, dc)
    await session_manager.start_session(user_id, acc_id, session_str)
    await state.clear()

    full_name = f"{fn} {ln}".strip() or "User"
    await status_msg.edit_text(
        f"🎉 **Account Successfully Added!**\n\n"
        f"• 👤 **Name:** `{full_name}`\n"
        f"• 📱 **Phone:** `{phone}`\n"
        f"• 🆔 **ID:** `{acc_id}`\n"
        f"• 🏢 **DC:** `DC{dc}`\n\n"
        f"Session database me store ho chuki hai aur active pool me ready hai!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 View Sessions", callback_data="hub_sessions")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
        ])
    )

@dp.message(LoginStates.waiting_for_phone)
async def handle_phone_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    raw_phone = (message.text or "").strip()
    phone_number = "+" + raw_phone.lstrip("+").replace(" ", "").replace("-", "")

    status_msg = await message.answer("⏳ Telegram se OTP request kiya ja raha hai...")
    client = session_manager.create_auth_client()

    try:
        await client.connect()
        send_code_res = await client.send_code_request(phone_number)
        phone_code_hash = send_code_res.phone_code_hash

        auth_clients[user_id] = {
            "client": client,
            "phone_number": phone_number,
            "phone_code_hash": phone_code_hash
        }
        await state.set_state(LoginStates.waiting_for_otp)

        await status_msg.edit_text(
            f"📩 **Telegram OTP Send Kar Diya Gaya Hai!**\n\n"
            f"Aapke Telegram app (`{phone_number}`) par ek 5-digit login code aaya hoga.\n\n"
            f"⚠️ **STRICT INSTRUCTION (Digits ke beech Space dein):**\n"
            f"Telegram security filter bypass karne ke liye **har number ke beech space dein!**\n\n"
            f"👉 **Aise likh kar bhejein:**\n"
            f"`1 2 3 4 5`\n\n"
            f"*(Agar code 91509 hai toh `9 1 5 0 9` bhejein)*",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]])
        )

    except PhoneNumberBannedError:
        if client.is_connected():
            await client.disconnect()
        await state.clear()
        await status_msg.edit_text("❌ Ye phone number Telegram par BANNED hai.")
    except PhoneNumberInvalidError:
        if client.is_connected():
            await client.disconnect()
        await status_msg.edit_text(
            "❌ **Phone number invalid hai!**\n\nKripya country code ke sath number bhejein (jaise `+919876543210`).",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Retry", callback_data="add_phone_otp")]])
        )
    except FloodWaitError as e:
        if client.is_connected():
            await client.disconnect()
        await state.clear()
        await status_msg.edit_text(f"⚠️ Telegram FloodWait: Kripya {e.seconds} seconds baad try karein.")
    except Exception as e:
        if client.is_connected():
            await client.disconnect()
        await state.clear()
        logger.error(f"Error sending code to {phone_number}: {e}")
        await status_msg.edit_text(
            f"❌ **Error:** `{e}`\n\nKripya String Session method try karein.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔑 Paste String Session", callback_data="add_string_session")],
                [InlineKeyboardButton(text="🔄 Retry Phone", callback_data="add_phone_otp")]
            ])
        )

@dp.message(LoginStates.waiting_for_otp)
async def handle_otp_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    otp_code = "".join(ch for ch in message.text if ch.isdigit())
    auth_data = auth_clients.get(user_id)

    if not auth_data or not auth_data.get("client"):
        await state.clear()
        await message.answer("⚠️ Login session expire ho gaya. Kripya shuru se start karein.", reply_markup=get_add_session_keyboard())
        return

    client: TelegramClient = auth_data["client"]
    phone_number = auth_data["phone_number"]
    phone_code_hash = auth_data["phone_code_hash"]

    status_msg = await message.answer("⏳ OTP verify kiya ja raha hai...")

    try:
        if not client.is_connected():
            await client.connect()

        user_obj = await client.sign_in(
            phone=phone_number,
            code=otp_code,
            phone_code_hash=phone_code_hash
        )

        session_str = client.session.save()
        dc_id = client.session.dc_id
        acc_id = user_obj.id
        fn = user_obj.first_name or ""
        ln = user_obj.last_name or ""
        un = user_obj.username or ""

        await client.disconnect()
        auth_clients.pop(user_id, None)

        await database.save_or_update_session(user_id, acc_id, phone_number, session_str, fn, ln, un, dc_id)
        await session_manager.start_session(user_id, acc_id, session_str)
        await state.clear()

        full_name = f"{fn} {ln}".strip() or "User"
        await status_msg.edit_text(
            f"🎉 **Login Successful! Account Added!**\n\n"
            f"• 👤 **Name:** `{full_name}`\n"
            f"• 📱 **Phone:** `{phone_number}`\n"
            f"• 🆔 **ID:** `{acc_id}`\n\n"
            f"Session pool me add ho chuka hai!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 View Sessions", callback_data="hub_sessions")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
            ])
        )

    except SessionPasswordNeededError:
        logger.info(f"Account {phone_number} requires 2FA password.")
        await state.set_state(LoginStates.waiting_for_2fa)
        await status_msg.edit_text(
            "🔐 **Two-Step Verification (2FA) Detected!**\n\n"
            "Aapke account par 2FA Cloud Password laga hua hai.\n\n"
            "👉 **Kripya apna 2FA Cloud Password yahan type karke bhejein:**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]])
        )

    except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
        await status_msg.edit_text(
            "❌ **OTP Galat Hai ya Expire Ho Chuka Hai!**\n\n"
            "⚠️ Kripya digits ke beech space dekar sahi code bhejein (jaise `1 2 3 4 5`):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Naya OTP Request Karein", callback_data="add_phone_otp")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]
            ])
        )
    except Exception as e:
        logger.error(f"Error signing in with OTP: {e}")
        await status_msg.edit_text(f"❌ **Login Error:** `{e}`")

@dp.message(LoginStates.waiting_for_2fa)
async def handle_2fa_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    password = (message.text or "").strip()
    auth_data = auth_clients.get(user_id)

    if not auth_data or not auth_data.get("client"):
        await state.clear()
        await message.answer("⚠️ Login session expire ho gaya. Kripya shuru se start karein.", reply_markup=get_add_session_keyboard())
        return

    client: TelegramClient = auth_data["client"]
    phone_number = auth_data["phone_number"]
    status_msg = await message.answer("⏳ 2FA Password verify kiya ja raha hai...")

    try:
        user_obj = await client.sign_in(password=password)
        session_str = client.session.save()
        dc_id = client.session.dc_id
        acc_id = user_obj.id
        fn = user_obj.first_name or ""
        ln = user_obj.last_name or ""
        un = user_obj.username or ""

        await client.disconnect()
        auth_clients.pop(user_id, None)

        await database.save_or_update_session(user_id, acc_id, phone_number, session_str, fn, ln, un, dc_id)
        await session_manager.start_session(user_id, acc_id, session_str)
        await state.clear()

        full_name = f"{fn} {ln}".strip() or "User"
        await status_msg.edit_text(
            f"🎉 **2FA Verified! Login 100% Successful!**\n\n"
            f"• 👤 **Name:** `{full_name}`\n"
            f"• 📱 **Phone:** `{phone_number}`\n"
            f"• 🆔 **ID:** `{acc_id}`\n\n"
            f"Account connected and ready!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 View Sessions", callback_data="hub_sessions")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")]
            ])
        )

    except PasswordHashInvalidError:
        await status_msg.edit_text(
            "❌ **2FA Password Galat Hai!**\n\nKripya sahi 2FA Password dobara enter karein:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="menu_main")]])
        )
    except Exception as e:
        logger.error(f"2FA sign in error: {e}")
        await status_msg.edit_text(f"❌ **2FA Error:** `{e}`")
