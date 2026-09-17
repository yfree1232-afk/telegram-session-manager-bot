from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard(owner_id: int = 0, user_id: int = 0) -> InlineKeyboardMarkup:
    """Aesthetic Main Menu Keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text="⚡ ɢᴇɴᴇʀᴀᴛᴇ sᴇssɪᴏɴ ⚡", callback_data="menu_generate")
        ],
        [
            InlineKeyboardButton(text="📱 ᴀᴄᴛɪᴠᴇ ᴅᴇᴠɪᴄᴇs", callback_data="menu_devices"),
            InlineKeyboardButton(text="💼 ᴀᴄᴄᴏᴜɴᴛ ᴠᴀᴜʟᴛ", callback_data="menu_vault")
        ],
        [
            InlineKeyboardButton(text="🛠 ᴜᴛɪʟɪᴛʏ ᴛᴏᴏʟs", callback_data="menu_tools"),
            InlineKeyboardButton(text="ℹ️ ᴀʙᴏᴜᴛ & ʜᴇʟᴘ", callback_data="menu_help")
        ]
    ]
    if owner_id and user_id == owner_id:
        buttons.append([InlineKeyboardButton(text="👑 ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def session_type_keyboard() -> InlineKeyboardMarkup:
    """Select Pyrogram or Telethon session."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🐍 ᴘʏʀᴏɢʀᴀᴍ (ᴠ2)", callback_data="gen_pyrogram"),
            InlineKeyboardButton(text="⚡ ᴛᴇʟᴇᴛʜᴏɴ", callback_data="gen_telethon")
        ],
        [
            InlineKeyboardButton(text="🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_main")
        ]
    ])

def api_choice_keyboard(session_type: str) -> InlineKeyboardMarkup:
    """Choose between Default API or Custom API credentials."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✨ ᴜsᴇ ᴅᴇғᴀᴜʟᴛ ᴀᴘɪ (ғᴀsᴛ)", callback_data=f"apichoice_default_{session_type}"),
        ],
        [
            InlineKeyboardButton(text="⚙️ ᴇɴᴛᴇʀ ᴍʏ ᴏᴡɴ ᴀᴘɪ_ɪᴅ / ʜᴀsʜ", callback_data=f"apichoice_custom_{session_type}")
        ],
        [
            InlineKeyboardButton(text="🔙 ᴄᴀɴᴄᴇʟ", callback_data="back_main")
        ]
    ])

def session_source_keyboard(action_type: str) -> InlineKeyboardMarkup:
    """Ask user whether to paste session string or choose from vault."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 ᴘᴀsᴛᴇ sᴇssɪᴏɴ sᴛʀɪɴɢ", callback_data=f"src_paste_{action_type}"),
            InlineKeyboardButton(text="💼 ғʀᴏᴍ ᴍʏ ᴠᴀᴜʟᴛ", callback_data=f"src_vault_{action_type}")
        ],
        [
            InlineKeyboardButton(text="🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_main")
        ]
    ])

def cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel operation button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ ᴄᴀɴᴄᴇʟ", callback_data="cancel_action")]
    ])

def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Simple back button to main menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="back_main")]
    ])

def save_to_vault_keyboard(session_type: str) -> InlineKeyboardMarkup:
    """Option to save newly generated session to vault."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 sᴀᴠᴇ ᴛᴏ ᴍʏ ᴠᴀᴜʟᴛ", callback_data=f"vault_save_recent_{session_type}")],
        [InlineKeyboardButton(text="🏠 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="back_main")]
    ])

def terminate_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm session termination."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚨 ʏᴇs, ᴛᴇʀᴍɪɴᴀᴛᴇ ɴᴏᴡ!", callback_data="confirm_term_all"),
            InlineKeyboardButton(text="❌ ᴄᴀɴᴄᴇʟ", callback_data="back_main")
        ]
    ])

def tools_menu_keyboard() -> InlineKeyboardMarkup:
    """Account tools options."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚪 ʟᴇᴀᴠᴇ ᴀʟʟ ᴄʜᴀɴɴᴇʟs & ɢʀᴏᴜᴘs", callback_data="tool_leave_chats")
        ],
        [
            InlineKeyboardButton(text="🔍 ᴄʜᴇᴄᴋ sᴇssɪᴏɴ ʜᴇᴀʟᴛʜ", callback_data="tool_check_health")
        ],
        [
            InlineKeyboardButton(text="🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_main")
        ]
    ])
