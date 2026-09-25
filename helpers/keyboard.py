from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard(owner_id: int = 0, user_id: int = 0, accounts_count: int = 0) -> InlineKeyboardMarkup:
    """1:1 Exact ICE BOT (@Oversout_bot) Clean Main Menu Grid."""
    buttons = [
        [
            InlineKeyboardButton(text="Read OTP", callback_data="a_read_otp")
        ],
        [
            InlineKeyboardButton(text="Check Sessions", callback_data="a_check"),
            InlineKeyboardButton(text="Spam Check", callback_data="a_spam")
        ],
        [
            InlineKeyboardButton(text="Contact Tool", callback_data="a_contact"),
            InlineKeyboardButton(text="2FA Manager", callback_data="a_2fa")
        ],
        [
            InlineKeyboardButton(text="Split File", callback_data="a_split"),
            InlineKeyboardButton(text="Session API Link", callback_data="cv_s2api")
        ],
        [
            InlineKeyboardButton(text="Merge Files", callback_data="merge_start")
        ],
        [
            InlineKeyboardButton(text="Create Session", callback_data="menu_generate"),
            InlineKeyboardButton(text="Device Cloner", callback_data="tool_fingerprints")
        ],
        [
            InlineKeyboardButton(text="Privacy Settings", callback_data="a_privacy"),
            InlineKeyboardButton(text="Check Age", callback_data="a_age")
        ],
        [
            InlineKeyboardButton(text="Converter", callback_data="a_convert"),
            InlineKeyboardButton(text="Leave Groups & Channels", callback_data="c_leavegc")
        ],
        [
            InlineKeyboardButton(text="Kill Sessions", callback_data="a_kill"),
            InlineKeyboardButton(text="Terminate All", callback_data="a_term")
        ],
        [
            InlineKeyboardButton(text="Clear Data", callback_data="a_clear")
        ],
        [
            InlineKeyboardButton(text="UserCenter", callback_data="user_center"),
            InlineKeyboardButton(text="Customer Support", callback_data="support_contact")
        ],
        [
            InlineKeyboardButton(text="Language", callback_data="lang_menu")
        ]
    ]
    if owner_id and user_id == owner_id:
        buttons.append([InlineKeyboardButton(text="Admin Control Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def session_type_keyboard() -> InlineKeyboardMarkup:
    """Select QR Code, Pyrogram, or Telethon session."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="QR Code Login (Instant)", callback_data="gen_qr")
        ],
        [
            InlineKeyboardButton(text="Pyrogram (v2)", callback_data="gen_pyrogram"),
            InlineKeyboardButton(text="Telethon", callback_data="gen_telethon")
        ],
        [
            InlineKeyboardButton(text="Cancel", callback_data="cancel_pending_op")
        ]
    ])

def session_phone_prompt_keyboard(session_type: str) -> InlineKeyboardMarkup:
    """Keyboard when prompting for phone number in session creation."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Device & API Settings", callback_data=f"gen_adv_{session_type}")
        ],
        [
            InlineKeyboardButton(text="Cancel", callback_data="cancel_pending_op")
        ]
    ])

def api_choice_keyboard(session_type: str) -> InlineKeyboardMarkup:
    """Choose between Default API or Custom API credentials."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Use Official Fast API", callback_data=f"apichoice_default_{session_type}"),
        ],
        [
            InlineKeyboardButton(text="Custom API_ID & Hash", callback_data=f"apichoice_custom_{session_type}")
        ],
        [
            InlineKeyboardButton(text="Cancel", callback_data="cancel_pending_op")
        ]
    ])

def session_source_keyboard(action_type: str) -> InlineKeyboardMarkup:
    """Ask user whether to paste session string or choose from vault."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Paste Session String", callback_data=f"src_paste_{action_type}"),
            InlineKeyboardButton(text="Select from Vault", callback_data=f"src_vault_{action_type}")
        ],
        [
            InlineKeyboardButton(text="Cancel", callback_data="cancel_pending_op")
        ]
    ])

def cancel_keyboard() -> InlineKeyboardMarkup:
    """Exact ICE BOT cancel button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Cancel", callback_data="cancel_pending_op")]
    ])

def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Exact ICE BOT back / cancel button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Back to Menu", callback_data="back_main")]
    ])

def language_keyboard() -> InlineKeyboardMarkup:
    """Exact ICE BOT language menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="English", callback_data="lang_set:en")],
        [InlineKeyboardButton(text="中文", callback_data="lang_set:zh")],
        [InlineKeyboardButton(text="Русский", callback_data="lang_set:ru")],
        [InlineKeyboardButton(text="বাংলা", callback_data="lang_set:bn")],
        [InlineKeyboardButton(text="Tiếng Việt", callback_data="lang_set:vi")],
        [InlineKeyboardButton(text="Cancel", callback_data="cancel_pending_op")]
    ])

def save_to_vault_keyboard(session_type: str) -> InlineKeyboardMarkup:
    """Option to save newly generated session to vault."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Save to Vault", callback_data=f"vault_save_recent_{session_type}")],
        [InlineKeyboardButton(text="Main Menu", callback_data="back_main")]
    ])

def terminate_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm session termination."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Yes, Terminate All Now", callback_data="confirm_term_all"),
            InlineKeyboardButton(text="Cancel", callback_data="back_main")
        ]
    ])

def tools_menu_keyboard() -> InlineKeyboardMarkup:
    """Account tools options."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Leave Groups & Channels", callback_data="c_leavegc")
        ],
        [
            InlineKeyboardButton(text="Delete All Dialogs", callback_data="tool_delete_dialogs")
        ],
        [
            InlineKeyboardButton(text="SpamBot Status", callback_data="a_spam"),
            InlineKeyboardButton(text="Check Session Health", callback_data="a_check")
        ],
        [
            InlineKeyboardButton(text="Back to Menu", callback_data="back_main")
        ]
    ])

def account_detail_keyboard(db_id: int) -> InlineKeyboardMarkup:
    """Detailed management options for a saved account."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Test / Ping", callback_data=f"check_acc_status_{db_id}"),
            InlineKeyboardButton(text="View Devices", callback_data=f"seldev_acc_{db_id}")
        ],
        [
            InlineKeyboardButton(text="SpamBot", callback_data=f"selspam_acc_{db_id}"),
            InlineKeyboardButton(text="2FA Status", callback_data=f"sel2fa_acc_{db_id}")
        ],
        [
            InlineKeyboardButton(text="Leave Chats", callback_data=f"selleave_acc_{db_id}"),
            InlineKeyboardButton(text="Delete Dialogs", callback_data=f"seldeldia_acc_{db_id}")
        ],
        [
            InlineKeyboardButton(text="View String", callback_data=f"acc_export_{db_id}"),
            InlineKeyboardButton(text="Remove from Vault", callback_data=f"del_acc_confirm_{db_id}")
        ],
        [
            InlineKeyboardButton(text="Back to Vault", callback_data="menu_vault"),
            InlineKeyboardButton(text="Main Menu", callback_data="back_main")
        ]
    ])

def fingerprints_selector_keyboard(mode: str = "gen") -> InlineKeyboardMarkup:
    """Select device fingerprint profile."""
    prefix = "fpgen_" if mode == "gen" else "fpview_"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Samsung Galaxy S24 Ultra", callback_data=f"{prefix}samsung"),
            InlineKeyboardButton(text="iPhone 15 Pro Max", callback_data=f"{prefix}iphone")
        ],
        [
            InlineKeyboardButton(text="Xiaomi 14 Pro", callback_data=f"{prefix}xiaomi"),
            InlineKeyboardButton(text="Windows 11 PC", callback_data=f"{prefix}desktop")
        ],
        [
            InlineKeyboardButton(text="MacBook Pro M3", callback_data=f"{prefix}macos"),
            InlineKeyboardButton(text="Official Telegram App", callback_data=f"{prefix}default")
        ],
        [
            InlineKeyboardButton(text="Cancel", callback_data="cancel_pending_op")
        ]
    ])

def user_center_keyboard() -> InlineKeyboardMarkup:
    """User center overview keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Open Vault", callback_data="menu_vault"),
            InlineKeyboardButton(text="Check All Health", callback_data="vault_check_all")
        ],
        [
            InlineKeyboardButton(text="Export Backup", callback_data="vault_export"),
            InlineKeyboardButton(text="Cancel", callback_data="cancel_pending_op")
        ]
    ])
