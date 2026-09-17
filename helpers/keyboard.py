from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard(owner_id: int = 0, user_id: int = 0, accounts_count: int = 0) -> InlineKeyboardMarkup:
    """Aesthetic Main Menu Keyboard with Bot API 9.4 colorful button styles."""
    buttons = [
        [
            InlineKeyboardButton(text="⚡ ɢᴇɴᴇʀᴀᴛᴇ sᴇssɪᴏɴ (ᴘʏʀᴏɢʀᴀᴍ & ᴛᴇʟᴇᴛʜᴏɴ) ⚡", callback_data="menu_generate", style="primary")
        ],
        [
            InlineKeyboardButton(text="🎙️ ᴠᴄ ᴀᴜᴛᴏ-ᴅᴍ & ʟɪᴠᴇ ʙʟᴀsᴛᴇʀ", callback_data="menu_vc", style="success")
        ],
        [
            InlineKeyboardButton(text="📱 ᴀᴄᴛɪᴠᴇ ᴅᴇᴠɪᴄᴇs & sᴇᴄᴜʀɪᴛʏ", callback_data="menu_devices", style="primary"),
            InlineKeyboardButton(text=f"👥 ᴍʏ ᴀᴄᴄᴏᴜɴᴛs ({accounts_count})", callback_data="menu_vault", style="primary")
        ],
        [
            InlineKeyboardButton(text="📡 ᴍᴜʟᴛɪ-ᴀᴄᴄᴏᴜɴᴛ ʙʀᴏᴀᴅᴄᴀsᴛ", callback_data="menu_broadcast", style="primary"),
            InlineKeyboardButton(text="🛠️ ᴜᴛɪʟɪᴛʏ ᴛᴏᴏʟs", callback_data="menu_tools", style="default")
        ],
        [
            InlineKeyboardButton(text="🔄 ᴘɪɴɢ ᴀʟʟ ᴀᴄᴄᴏᴜɴᴛs", callback_data="vault_check_all", style="success"),
            InlineKeyboardButton(text="ℹ️ ʜᴇʟᴘ & ɢᴜɪᴅᴇ", callback_data="menu_help", style="default")
        ]
    ]
    if owner_id and user_id == owner_id:
        buttons.append([InlineKeyboardButton(text="👑 ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ", callback_data="admin_panel", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def session_type_keyboard() -> InlineKeyboardMarkup:
    """Select Pyrogram or Telethon session."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🐍 ᴘʏʀᴏɢʀᴀᴍ (ᴠ2)", callback_data="gen_pyrogram", style="primary"),
            InlineKeyboardButton(text="⚡ ᴛᴇʟᴇᴛʜᴏɴ", callback_data="gen_telethon", style="primary")
        ],
        [
            InlineKeyboardButton(text="🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_main", style="default")
        ]
    ])

def api_choice_keyboard(session_type: str) -> InlineKeyboardMarkup:
    """Choose between Default API or Custom API credentials."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✨ ᴜsᴇ ᴅᴇғᴀᴜʟᴛ ᴏғғɪᴄɪᴀʟ ᴀᴘɪ (ғᴀsᴛ)", callback_data=f"apichoice_default_{session_type}", style="success"),
        ],
        [
            InlineKeyboardButton(text="⚙️ ᴇɴᴛᴇʀ ᴍʏ ᴏᴡɴ ᴀᴘɪ_ɪᴅ / ʜᴀsʜ", callback_data=f"apichoice_custom_{session_type}", style="primary")
        ],
        [
            InlineKeyboardButton(text="🔙 ᴄᴀɴᴄᴇʟ", callback_data="back_main", style="danger")
        ]
    ])

def session_source_keyboard(action_type: str) -> InlineKeyboardMarkup:
    """Ask user whether to paste session string or choose from vault."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 ᴘᴀsᴛᴇ sᴇssɪᴏɴ sᴛʀɪɴɢ", callback_data=f"src_paste_{action_type}", style="primary"),
            InlineKeyboardButton(text="💼 ғʀᴏᴍ ᴍʏ ᴠᴀᴜʟᴛ", callback_data=f"src_vault_{action_type}", style="success")
        ],
        [
            InlineKeyboardButton(text="🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_main", style="default")
        ]
    ])

def cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel operation button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ ᴄᴀɴᴄᴇʟ", callback_data="cancel_action", style="danger")]
    ])

def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Simple back button to main menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="back_main", style="default")]
    ])

def save_to_vault_keyboard(session_type: str) -> InlineKeyboardMarkup:
    """Option to save newly generated session to vault."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 sᴀᴠᴇ ᴛᴏ ᴍʏ ᴠᴀᴜʟᴛ", callback_data=f"vault_save_recent_{session_type}", style="success")],
        [InlineKeyboardButton(text="🏠 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="back_main", style="default")]
    ])

def terminate_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm session termination."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚨 ʏᴇs, ᴛᴇʀᴍɪɴᴀᴛᴇ ᴀʟʟ ɴᴏᴡ!", callback_data="confirm_term_all", style="danger"),
            InlineKeyboardButton(text="❌ ᴄᴀɴᴄᴇʟ", callback_data="back_main", style="default")
        ]
    ])

def tools_menu_keyboard() -> InlineKeyboardMarkup:
    """Account tools options."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚪 ʟᴇᴀᴠᴇ ᴀʟʟ ᴄʜᴀɴɴᴇʟs & ɢʀᴏᴜᴘs", callback_data="tool_leave_chats", style="danger")
        ],
        [
            InlineKeyboardButton(text="🗑️ ᴅᴇʟᴇᴛᴇ ᴀʟʟ ᴅɪᴀʟᴏɢs / ᴄʜᴀᴛs", callback_data="tool_delete_dialogs", style="danger")
        ],
        [
            InlineKeyboardButton(text="🛡️ ᴄʜᴇᴄᴋ ʙᴀɴ & sᴘᴀᴍʙᴏᴛ sᴛᴀᴛᴜs", callback_data="tool_check_spambot", style="primary"),
            InlineKeyboardButton(text="🔍 ᴄʜᴇᴄᴋ sᴇssɪᴏɴ ʜᴇᴀʟᴛʜ", callback_data="tool_check_health", style="primary")
        ],
        [
            InlineKeyboardButton(text="🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_main", style="default")
        ]
    ])

def vc_dashboard_keyboard(user_data: dict | None = None) -> InlineKeyboardMarkup:
    """Voice Chat (VC) Auto-DM configuration keyboard with colorful styles."""
    delay = user_data.get("vc_delay", 2.5) if user_data else 2.5
    is_auto_on = bool(user_data and user_data.get("vc_auto_send") == 1)

    if is_auto_on:
        auto_toggle_text = "⚡ Real-Time Auto-DM: 🟢 ON (Running)"
        auto_style = "success"
    else:
        auto_toggle_text = "⚡ Real-Time Auto-DM: 🔴 OFF (Click to ON)"
        auto_style = "danger"

    buttons = [
        [
            InlineKeyboardButton(text=auto_toggle_text, callback_data="vc_toggle_auto", style=auto_style)
        ],
        [
            InlineKeyboardButton(text="🎛️ Select Sender Accounts (ON/OFF)", callback_data="vc_select_accounts", style="primary")
        ],
        [
            InlineKeyboardButton(text="🔍 Auto-Detect Live VCs (1-Click)", callback_data="vc_auto_detect", style="primary"),
            InlineKeyboardButton(text="🚀 Send Manual Link", callback_data="vc_send_blast", style="primary")
        ],
        [
            InlineKeyboardButton(text="✍️ Edit VC Custom Message", callback_data="vc_edit_msg", style="primary"),
            InlineKeyboardButton(text=f"⏱️ Delay: {delay}s", callback_data="vc_delay_menu", style="default")
        ],
        [
            InlineKeyboardButton(text="📊 VC Sent Stats", callback_data="vc_stats", style="default"),
            InlineKeyboardButton(text="🔄 Reset VC Message", callback_data="vc_reset_msg", style="danger")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to Main Dashboard", callback_data="back_main", style="default")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def account_toggle_switch_keyboard(accounts: list[dict]) -> InlineKeyboardMarkup:
    """Generate 1-click ON/OFF toggle switch list for all connected accounts."""
    buttons = []
    if not accounts:
        buttons.append([
            InlineKeyboardButton(text="➕ Koi Account nahi mila. Add Karein!", callback_data="vault_add_acc", style="success")
        ])
    else:
        for acc in accounts:
            db_id = acc["id"]
            phone = acc.get("phone_number") or acc.get("phone", "Unknown")
            name = acc.get("first_name", "") or acc.get("account_name", "") or "User"
            is_active = acc.get("is_active", 1)

            if is_active == 1:
                btn_text = f"🟢 {phone} ({name[:10]}) ➔ [ON]"
                btn_style = "success"
            else:
                btn_text = f"🔴 {phone} ({name[:10]}) ➔ [OFF]"
                btn_style = "danger"

            buttons.append([
                InlineKeyboardButton(text=btn_text, callback_data=f"acc_quick_toggle_{db_id}", style=btn_style)
            ])

        buttons.append([
            InlineKeyboardButton(text="🟢 Enable All (Sab ON)", callback_data="acc_toggle_all_1", style="success"),
            InlineKeyboardButton(text="🔴 Disable All (Sab OFF)", callback_data="acc_toggle_all_0", style="danger")
        ])

    buttons.append([
        InlineKeyboardButton(text="🔙 Back to VC Dashboard", callback_data="menu_vc", style="default")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def detected_vcs_keyboard(vcs: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard listing auto-detected live Voice Chats."""
    buttons = []
    if not vcs:
        buttons.append([
            InlineKeyboardButton(text="⚠️ Koi Live VC nahi mila", callback_data="vc_auto_detect", style="default")
        ])
    else:
        for v in vcs:
            cid = str(v.get("id"))
            title = v.get("title", "Voice Chat")
            if len(title) > 20:
                title = title[:20] + ".."
            p_cnt = v.get("participants_count", 0)
            btn_text = f"🎙️ {title} ({p_cnt} in VC)"
            buttons.append([
                InlineKeyboardButton(text=btn_text, callback_data=f"vc_blast_target_{cid}", style="success")
            ])

    buttons.append([
        InlineKeyboardButton(text="🔄 Scan Again", callback_data="vc_auto_detect", style="primary"),
        InlineKeyboardButton(text="🔗 Enter Link Manually", callback_data="vc_send_blast", style="primary")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Back to VC Dashboard", callback_data="menu_vc", style="default")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def vc_delay_keyboard() -> InlineKeyboardMarkup:
    """Anti-ban delay selector."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ Fast (1.5s)", callback_data="vc_set_delay_1.5", style="primary"),
            InlineKeyboardButton(text="🛡️ Safe (2.5s - Recommended)", callback_data="vc_set_delay_2.5", style="success")
        ],
        [
            InlineKeyboardButton(text="🔒 Ultra-Safe (5.0s)", callback_data="vc_set_delay_5.0", style="primary"),
            InlineKeyboardButton(text="🐢 Relaxed (8.0s)", callback_data="vc_set_delay_8.0", style="default")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to VC Menu", callback_data="menu_vc", style="default")
        ]
    ])

def live_vc_blaster_keyboard() -> InlineKeyboardMarkup:
    """Controls for active real-time continuous VC blaster."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏹️ Stop VC Blast", callback_data="vc_stop_blast", style="danger")
        ],
        [
            InlineKeyboardButton(text="🎙️ VC Dashboard", callback_data="menu_vc", style="primary"),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main", style="default")
        ]
    ])

def login_method_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting login method with colorful styling."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 Phone + OTP (Interactive Login)", callback_data="btn_phone_login", style="success")
        ],
        [
            InlineKeyboardButton(text="🔑 Direct Session String (Telethon/Pyrogram)", callback_data="btn_session_login", style="primary")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="back_main", style="default")
        ]
    ])

def account_detail_keyboard(db_id: int, is_active: int, status: str = "ACTIVE") -> InlineKeyboardMarkup:
    """Keyboard for specific account view & actions."""
    toggle_text = "⏸️ Pause Account" if is_active == 1 else "▶️ Activate Account"
    toggle_style = "danger" if is_active == 1 else "success"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Test / Ping Session", callback_data=f"acc_ping_{db_id}", style="primary"),
            InlineKeyboardButton(text=toggle_text, callback_data=f"acc_toggle_{db_id}", style=toggle_style)
        ],
        [
            InlineKeyboardButton(text="🔑 View Session String", callback_data=f"acc_export_{db_id}", style="primary"),
            InlineKeyboardButton(text="🗑️ Logout & Remove", callback_data=f"acc_del_confirm_{db_id}", style="danger")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to Accounts List", callback_data="menu_vault", style="default"),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main", style="default")
        ]
    ])

