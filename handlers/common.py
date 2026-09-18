import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client as PyroClient
from telethon import TelegramClient

ACTIVE_LOGINS: dict[int, dict] = {}
RECENT_SESSIONS: dict[int, dict] = {}
INSPECT_CACHE: dict[int, dict] = {}

def detect_session_type(session_str: str) -> str:
    s = session_str.strip()
    if s.startswith("1") and len(s) > 200:
        return "telethon"
    return "pyrogram"

async def cleanup_user_login(user_id: int):
    login_data = ACTIVE_LOGINS.pop(user_id, None)
    if login_data and "client" in login_data:
        c = login_data["client"]
        try:
            if isinstance(c, PyroClient):
                if c.is_connected:
                    await c.disconnect()
            elif isinstance(c, TelegramClient):
                if c.is_connected():
                    await c.disconnect()
        except Exception:
            pass

START_TEXT = """
<tg-emoji emoji-id="5931718859366075705">✨</tg-emoji> <b>WELCOME TO ICE BOT</b>
━━━━━━━━━━━━━━━━━━━━

<tg-emoji emoji-id="5926906120877640711">🛡️</tg-emoji> Trusted workspace • 100% safe handling
<tg-emoji emoji-id="5852777287451151788">🟢</tg-emoji> Free mode active
<tg-emoji emoji-id="5931723180103175243">📥</tg-emoji> Upload <code>.session</code>, <code>.zip</code>, or <code>.json</code> to begin.
<tg-emoji emoji-id="5971867376130461576">💠</tg-emoji> Choose any operation from the menu below.
""".strip()

HELP_TEXT = """
📖 <b>𝗜𝗖𝗘 𝗕𝗢𝗧 • 𝗨𝗦𝗘𝗥 𝗚𝗨𝗜𝗗𝗘</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣ <b>⚡ Generate String Session:</b>
• Click <code>⚡ Generate Session</code>.
• Choose <b>Pyrogram (v2)</b> or <b>Telethon</b>.
• Select <i>Official Fast API</i> or enter custom API credentials.
• Enter your phone number with country code (e.g. <code>+919876543210</code>).
• Enter OTP (use spaces like <code>1 2 3 4 5</code> if needed).
• Enter 2FA password if enabled.
• The session string is sent in a <b>copyable box</b>, sent to your <b>Saved Messages</b>, and can be saved to your <b>Encrypted Vault</b> with 1 click!

2️⃣ <b>📱 Active Devices & Remote Kill:</b>
• Paste any session string OR select an account from your Vault.
• See all connected devices, device models, OS, app version, IP, country, and active time.
• Click <b>Terminate All Other Sessions</b> to immediately disconnect all unknown devices!

3️⃣ <b>🛡️ SpamBot Status Checker:</b>
• Check whether an account is limited, muted, or clean by querying @SpamBot in real-time.

4️⃣ <b>🔐 2FA Security Audit:</b>
• Verify if Two-Step Verification is active, see the password hint, and check if recovery email is bound.

5️⃣ <b>👤 Account Info Inspector:</b>
• Full profile breakdown: User ID, DC ID (Miami/Amsterdam/Singapore), phone, premium badge, dialog counts, and active devices.

6️⃣ <b>🚪 Leave All Channels & Groups:</b>
• Clean up your account by leaving all joined channels and public groups with 1 click.

7️⃣ <b>🗑️ Delete All Dialogs:</b>
• Clear all private messages and chats for maximum privacy.

8️⃣ <b>💼 Encrypted Vault & Backup:</b>
• Store accounts securely with AES-Fernet cloud encryption.
• Ping accounts, export a complete <code>.txt</code> backup file, or manage anytime!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

