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
❄️ <b>𝗜𝗖𝗘 𝗕𝗢𝗧 • 𝗦𝗘𝗦𝗦𝗜𝗢𝗡 𝗠𝗔𝗡𝗔𝗚𝗘𝗥</b> ❄️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👋 <b>Welcome, {name}!</b>

<blockquote><i>The Most Powerful & Aesthetic Telegram Session Generator & Account Security Suite. High-speed, secure, and multi-functional.</i></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <b>String Generator:</b> Pyrogram v2 & Telethon (Fast & Safe)
📱 <b>Device Manager:</b> Active Logins, IPs & 1-Click Terminate All
🛡️ <b>SpamBot Status:</b> Real-time limitation check via @SpamBot
🔐 <b>2FA Security:</b> Two-step verification audit & vulnerability check
🚪 <b>Leave All Chats:</b> 1-Click exit all channels & supergroups
🗑️ <b>Delete Dialogs:</b> Clear all private chats & dialog inbox
👤 <b>Account Info:</b> DC ID, User ID, Premium status, channels count
💼 <b>Saved Vault:</b> AES-256 Encrypted MongoDB Cloud Storage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 <b>Database:</b> <i>MongoDB Atlas Cloud (AES-256 Encrypted)</i>
"""

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

