from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard(owner_id: int = 0, user_id: int = 0, accounts_count: int = 0) -> InlineKeyboardMarkup:
    """Aesthetic ICE BOT Main Menu with Bot API 9.4 colorful button styles."""
    buttons = [
        [
            InlineKeyboardButton(text="⚡ ɢᴇɴᴇʀᴀᴛᴇ sᴇssɪᴏɴ (ᴘʏʀᴏɢʀᴀᴍ & ᴛᴇʟᴇᴛʜᴏɴ) ⚡", callback_data="menu_generate", style="primary")
        ],
        [
            InlineKeyboardButton(text="📱 ᴀᴄᴛɪᴠᴇ ᴅᴇᴠɪᴄᴇs", callback_data="menu_devices", style="primary"),
            InlineKeyboardButton(text=f"💼 sᴀᴠᴇᴅ ᴀᴄᴄᴏᴜɴᴛs ({accounts_count})", callback_data="menu_vault", style="primary")
        ],
        [
            InlineKeyboardButton(text="🛡️ sᴘᴀᴍʙᴏᴛ sᴛᴀᴛᴜs", callback_data="tool_check_spambot", style="success"),
            InlineKeyboardButton(text="🔐 𝟸ғᴀ sᴇᴄᴜʀɪᴛʏ ᴄʜᴇᴄᴋ", callback_data="tool_check_2fa", style="primary")
        ],
        [
            InlineKeyboardButton(text="🚪 ʟᴇᴀᴠᴇ ᴀʟʟ ᴄʜᴀᴛs", callback_data="tool_leave_chats", style="danger"),
            InlineKeyboardButton(text="🗑️ ᴅᴇʟᴇᴛᴇ ᴀʟʟ ᴅɪᴀʟᴏɢs", callback_data="tool_delete_dialogs", style="danger")
        ],
        [
            InlineKeyboardButton(text="👤 ᴀᴄᴄᴏᴜɴᴛ ɪɴғᴏ", callback_data="tool_acc_info", style="primary"),
            InlineKeyboardButton(text="🔄 ᴄʜᴇᴄᴋ ᴀʟʟ ʜᴇᴀʟᴛʜ", callback_data="vault_check_all", style="success")
        ],
        [
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

def account_detail_keyboard(db_id: int) -> InlineKeyboardMarkup:
    """Detailed management options for a saved account."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 ᴛᴇsᴛ / ᴘɪɴɢ", callback_data=f"check_acc_status_{db_id}", style="primary"),
            InlineKeyboardButton(text="📱 ᴠɪᴇᴡ ᴅᴇᴠɪᴄᴇs", callback_data=f"seldev_acc_{db_id}", style="primary")
        ],
        [
            InlineKeyboardButton(text="🛡️ sᴘᴀᴍʙᴏᴛ", callback_data=f"selspam_acc_{db_id}", style="success"),
            InlineKeyboardButton(text="🔐 𝟸ғᴀ sᴛᴀᴛᴜs", callback_data=f"sel2fa_acc_{db_id}", style="primary")
        ],
        [
            InlineKeyboardButton(text="🚪 ʟᴇᴀᴠᴇ ᴄʜᴀᴛs", callback_data=f"selleave_acc_{db_id}", style="danger"),
            InlineKeyboardButton(text="🗑️ ᴅᴇʟᴇᴛᴇ ᴅɪᴀʟᴏɢs", callback_data=f"seldeldia_acc_{db_id}", style="danger")
        ],
        [
            InlineKeyboardButton(text="🔑 ᴠɪᴇᴡ sᴛʀɪɴɢ", callback_data=f"acc_export_{db_id}", style="primary"),
            InlineKeyboardButton(text="❌ ʀᴇᴍᴏᴠᴇ ғʀᴏᴍ ᴠᴀᴜʟᴛ", callback_data=f"del_acc_confirm_{db_id}", style="danger")
        ],
        [
            InlineKeyboardButton(text="🔙 ʙᴀᴄᴋ ᴛᴏ ᴠᴀᴜʟᴛ", callback_data="menu_vault", style="default"),
            InlineKeyboardButton(text="🏠 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="back_main", style="default")
        ]
    ])

