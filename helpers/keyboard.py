from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Telegram Verified Premium Custom Emoji IDs (Bot API 9.4)
EMOJI_OTP = "5406935634575124018"       # Mail / Envelope
EMOJI_SEARCH = "5427009714745511175"    # Magnifying Glass / Check
EMOJI_SHIELD = "5420319635037775013"    # Security Shield / 2FA / Spam
EMOJI_USER = "5409180749876174620"      # User Profile / Contact / Device
EMOJI_TOOL = "5465451996544837861"      # Split / Merge / Scissors / Files
EMOJI_BOLT = "5445284980978621387"      # Lightning Bolt / API / Fast Action / Convert
EMOJI_EYE = "5449762358052266525"       # Eye / Privacy
EMOJI_STAR = "5431442100417749005"      # Star / Calendar / Support / Age
EMOJI_DANGER = "5465665476988315663"    # Fire / Trash / Kill / Terminate / Cancel
EMOJI_GLOBE = "5431736730032043640"     # Globe / Language

def main_menu_keyboard(owner_id: int = 0, user_id: int = 0, accounts_count: int = 0) -> InlineKeyboardMarkup:
    """1:1 Exact ICE BOT (@Oversout_bot) Main Menu Grid with Premium Custom Emojis."""
    buttons = [
        [
            InlineKeyboardButton(text="📩 ʀᴇᴀᴅ ᴏᴛᴘ", callback_data="a_read_otp", icon_custom_emoji_id=EMOJI_OTP)
        ],
        [
            InlineKeyboardButton(text="🔍 ᴄʜᴇᴄᴋ sᴇssɪᴏɴs", callback_data="a_check", icon_custom_emoji_id=EMOJI_SEARCH),
            InlineKeyboardButton(text="🛡️ sᴘᴀᴍ ᴄʜᴇᴄᴋ", callback_data="a_spam", icon_custom_emoji_id=EMOJI_SHIELD)
        ],
        [
            InlineKeyboardButton(text="👥 ᴄᴏɴᴛᴀᴄᴛ ᴛᴏᴏʟ", callback_data="a_contact", icon_custom_emoji_id=EMOJI_USER),
            InlineKeyboardButton(text="🔐 𝟸ғᴀ ᴍᴀɴᴀɢᴇʀ", callback_data="a_2fa", icon_custom_emoji_id=EMOJI_SHIELD)
        ],
        [
            InlineKeyboardButton(text="✂️ sᴘʟɪᴛ ғɪʟᴇ", callback_data="a_split", icon_custom_emoji_id=EMOJI_TOOL),
            InlineKeyboardButton(text="⚡ sᴇssɪᴏɴ ᴀᴘɪ ʟɪɴᴋ", callback_data="cv_s2api", icon_custom_emoji_id=EMOJI_BOLT)
        ],
        [
            InlineKeyboardButton(text="📁 ᴍᴇʀɢᴇ ғɪʟᴇs", callback_data="merge_start", icon_custom_emoji_id=EMOJI_TOOL)
        ],
        [
            InlineKeyboardButton(text="⚡ ᴄʀᴇᴀᴛᴇ sᴇssɪᴏɴ", callback_data="menu_generate", icon_custom_emoji_id=EMOJI_BOLT),
            InlineKeyboardButton(text="📱 ᴅᴇᴠɪᴄᴇ ᴄʟᴏɴᴇʀ", callback_data="tool_fingerprints", icon_custom_emoji_id=EMOJI_USER)
        ],
        [
            InlineKeyboardButton(text="👁️ ᴘʀɪᴠᴀᴄʏ sᴇᴛᴛɪɴɢs", callback_data="a_privacy", icon_custom_emoji_id=EMOJI_EYE),
            InlineKeyboardButton(text="📅 ᴄʜᴇᴄᴋ ᴀɢᴇ", callback_data="a_age", icon_custom_emoji_id=EMOJI_STAR)
        ],
        [
            InlineKeyboardButton(text="🔄 ᴄᴏɴᴠᴇʀᴛᴇʀ", callback_data="a_convert", icon_custom_emoji_id=EMOJI_BOLT),
            InlineKeyboardButton(text="🚪 ʟᴇᴀᴠᴇ ɢʀᴏᴜᴘs & ᴄʜᴀɴɴᴇʟs", callback_data="c_leavegc", icon_custom_emoji_id=EMOJI_DANGER)
        ],
        [
            InlineKeyboardButton(text="🔥 ᴋɪʟʟ sᴇssɪᴏɴs", callback_data="a_kill", icon_custom_emoji_id=EMOJI_DANGER),
            InlineKeyboardButton(text="🚨 ᴛᴇʀᴍɪɴᴀᴛᴇ ᴀʟʟ", callback_data="a_term", icon_custom_emoji_id=EMOJI_DANGER)
        ],
        [
            InlineKeyboardButton(text="🗑️ ᴄʟᴇᴀʀ ᴅᴀᴛᴀ", callback_data="a_clear", icon_custom_emoji_id=EMOJI_DANGER)
        ],
        [
            InlineKeyboardButton(text="👤 ᴜsᴇʀᴄᴇɴᴛᴇʀ", callback_data="user_center", icon_custom_emoji_id=EMOJI_USER),
            InlineKeyboardButton(text="🆘 ᴄᴜsᴛᴏᴍᴇʀ sᴜᴘᴘᴏʀᴛ", callback_data="support_contact", icon_custom_emoji_id=EMOJI_STAR)
        ],
        [
            InlineKeyboardButton(text="🌐 ʟᴀɴɢᴜᴀɢᴇ", callback_data="lang_menu", icon_custom_emoji_id=EMOJI_GLOBE)
        ]
    ]
    if owner_id and user_id == owner_id:
        buttons.append([InlineKeyboardButton(text="👑 ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ", callback_data="admin_panel", icon_custom_emoji_id=EMOJI_SHIELD)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def session_type_keyboard() -> InlineKeyboardMarkup:
    """Select Pyrogram or Telethon session."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ ᴘʏʀᴏɢʀᴀᴍ (ᴠ𝟸)", callback_data="gen_pyrogram", icon_custom_emoji_id=EMOJI_BOLT),
            InlineKeyboardButton(text="⚡ ᴛᴇʟᴇᴛʜᴏɴ", callback_data="gen_telethon", icon_custom_emoji_id=EMOJI_BOLT)
        ],
        [
            InlineKeyboardButton(text="✖️ ᴄᴀɴᴄᴇʟ", callback_data="cancel_pending_op", icon_custom_emoji_id=EMOJI_DANGER)
        ]
    ])

def session_phone_prompt_keyboard(session_type: str) -> InlineKeyboardMarkup:
    """Keyboard when prompting for phone number in session creation."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚙️ Device / Custom API Settings", callback_data=f"gen_adv_{session_type}", icon_custom_emoji_id=EMOJI_TOOL)
        ],
        [
            InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op", icon_custom_emoji_id=EMOJI_DANGER)
        ]
    ])

def api_choice_keyboard(session_type: str) -> InlineKeyboardMarkup:
    """Choose between Default API or Custom API credentials."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✨ Use Default Official API", callback_data=f"apichoice_default_{session_type}", icon_custom_emoji_id=EMOJI_BOLT),
        ],
        [
            InlineKeyboardButton(text="⚙️ Custom API_ID / Hash", callback_data=f"apichoice_custom_{session_type}", icon_custom_emoji_id=EMOJI_SEARCH)
        ],
        [
            InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op", icon_custom_emoji_id=EMOJI_DANGER)
        ]
    ])

def session_source_keyboard(action_type: str) -> InlineKeyboardMarkup:
    """Ask user whether to paste session string or choose from vault."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Paste Session String", callback_data=f"src_paste_{action_type}", icon_custom_emoji_id=EMOJI_OTP),
            InlineKeyboardButton(text="💼 Select From Vault", callback_data=f"src_vault_{action_type}", icon_custom_emoji_id=EMOJI_USER)
        ],
        [
            InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op", icon_custom_emoji_id=EMOJI_DANGER)
        ]
    ])

def cancel_keyboard() -> InlineKeyboardMarkup:
    """Exact ICE BOT cancel button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op", icon_custom_emoji_id=EMOJI_DANGER)]
    ])

def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Exact ICE BOT back / cancel button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op", icon_custom_emoji_id=EMOJI_DANGER)]
    ])

def language_keyboard() -> InlineKeyboardMarkup:
    """Exact ICE BOT language menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_set:en", icon_custom_emoji_id=EMOJI_GLOBE)],
        [InlineKeyboardButton(text="🇨🇳 中文", callback_data="lang_set:zh", icon_custom_emoji_id=EMOJI_GLOBE)],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_set:ru", icon_custom_emoji_id=EMOJI_GLOBE)],
        [InlineKeyboardButton(text="🇧🇩 বাংলা", callback_data="lang_set:bn", icon_custom_emoji_id=EMOJI_GLOBE)],
        [InlineKeyboardButton(text="🇻🇳 Tiếng Việt", callback_data="lang_set:vi", icon_custom_emoji_id=EMOJI_GLOBE)],
        [InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op", icon_custom_emoji_id=EMOJI_DANGER)]
    ])

def save_to_vault_keyboard(session_type: str) -> InlineKeyboardMarkup:
    """Option to save newly generated session to vault."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Save To Vault", callback_data=f"vault_save_recent_{session_type}", icon_custom_emoji_id=EMOJI_USER)],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main", icon_custom_emoji_id=EMOJI_STAR)]
    ])

def terminate_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm session termination."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚨 Yes, Terminate All Now!", callback_data="confirm_term_all", icon_custom_emoji_id=EMOJI_DANGER),
            InlineKeyboardButton(text="✖️ Cancel", callback_data="back_main", icon_custom_emoji_id=EMOJI_DANGER)
        ]
    ])

def tools_menu_keyboard() -> InlineKeyboardMarkup:
    """Account tools options."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚪 Leave All Channels & Groups", callback_data="tool_leave_chats", icon_custom_emoji_id=EMOJI_DANGER)
        ],
        [
            InlineKeyboardButton(text="🗑️ Delete All Dialogs / Chats", callback_data="tool_delete_dialogs", icon_custom_emoji_id=EMOJI_DANGER)
        ],
        [
            InlineKeyboardButton(text="🛡️ Check Ban & SpamBot Status", callback_data="tool_check_spambot", icon_custom_emoji_id=EMOJI_SHIELD),
            InlineKeyboardButton(text="🔍 Check Session Health", callback_data="tool_check_health", icon_custom_emoji_id=EMOJI_SEARCH)
        ],
        [
            InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_main", icon_custom_emoji_id=EMOJI_DANGER)
        ]
    ])

def account_detail_keyboard(db_id: int) -> InlineKeyboardMarkup:
    """Detailed management options for a saved account."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Test / Ping", callback_data=f"check_acc_status_{db_id}", icon_custom_emoji_id=EMOJI_SEARCH),
            InlineKeyboardButton(text="📱 View Devices", callback_data=f"seldev_acc_{db_id}", icon_custom_emoji_id=EMOJI_USER)
        ],
        [
            InlineKeyboardButton(text="🛡️ SpamBot", callback_data=f"selspam_acc_{db_id}", icon_custom_emoji_id=EMOJI_SHIELD),
            InlineKeyboardButton(text="🔐 2FA Status", callback_data=f"sel2fa_acc_{db_id}", icon_custom_emoji_id=EMOJI_SHIELD)
        ],
        [
            InlineKeyboardButton(text="🚪 Leave Chats", callback_data=f"selleave_acc_{db_id}", icon_custom_emoji_id=EMOJI_DANGER),
            InlineKeyboardButton(text="🗑️ Delete Dialogs", callback_data=f"seldeldia_acc_{db_id}", icon_custom_emoji_id=EMOJI_DANGER)
        ],
        [
            InlineKeyboardButton(text="🔑 View String", callback_data=f"acc_export_{db_id}", icon_custom_emoji_id=EMOJI_BOLT),
            InlineKeyboardButton(text="❌ Remove from Vault", callback_data=f"del_acc_confirm_{db_id}", icon_custom_emoji_id=EMOJI_DANGER)
        ],
        [
            InlineKeyboardButton(text="💼 Back to Vault", callback_data="menu_vault", icon_custom_emoji_id=EMOJI_USER),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main", icon_custom_emoji_id=EMOJI_STAR)
        ]
    ])

def fingerprints_selector_keyboard(mode: str = "gen") -> InlineKeyboardMarkup:
    """Select device fingerprint profile."""
    prefix = "fpgen_" if mode == "gen" else "fpview_"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 Samsung Galaxy S24 Ultra", callback_data=f"{prefix}samsung", icon_custom_emoji_id=EMOJI_USER),
            InlineKeyboardButton(text="🍏 iPhone 15 Pro Max", callback_data=f"{prefix}iphone", icon_custom_emoji_id=EMOJI_USER)
        ],
        [
            InlineKeyboardButton(text="📱 Xiaomi 14 Pro", callback_data=f"{prefix}xiaomi", icon_custom_emoji_id=EMOJI_USER),
            InlineKeyboardButton(text="💻 Windows 11 PC", callback_data=f"{prefix}desktop", icon_custom_emoji_id=EMOJI_USER)
        ],
        [
            InlineKeyboardButton(text="🍎 MacBook Pro M3", callback_data=f"{prefix}macos", icon_custom_emoji_id=EMOJI_USER),
            InlineKeyboardButton(text="⚡ Official Telegram App", callback_data=f"{prefix}default", icon_custom_emoji_id=EMOJI_BOLT)
        ],
        [
            InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op", icon_custom_emoji_id=EMOJI_DANGER)
        ]
    ])

def user_center_keyboard() -> InlineKeyboardMarkup:
    """User center overview keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💼 Open Encrypted Vault", callback_data="menu_vault", icon_custom_emoji_id=EMOJI_USER),
            InlineKeyboardButton(text="🔍 Check All Health", callback_data="vault_check_all", icon_custom_emoji_id=EMOJI_SEARCH)
        ],
        [
            InlineKeyboardButton(text="📤 Export Backup File", callback_data="vault_export", icon_custom_emoji_id=EMOJI_TOOL),
            InlineKeyboardButton(text="✖️ Cancel", callback_data="cancel_pending_op", icon_custom_emoji_id=EMOJI_DANGER)
        ]
    ])



