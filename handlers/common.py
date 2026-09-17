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
╔══════════════════════════╗
║  ⚡ <b>𝗦𝗘𝗦𝗦𝗜𝗢𝗡 𝗠𝗔𝗡𝗔𝗚𝗘𝗥 𝗩𝗢𝗟𝗧𝗫</b> ⚡  ║
╚══════════════════════════╝
👋 <b>Welcome, {name}!</b>

<blockquote><i>The most advanced Telegram Session Suite for Pyrogram & Telethon accounts.</i></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <b>String Generator:</b> Pyrogram v2 & Telethon
📱 <b>Device Manager:</b> View Active IPs & Terminate
💼 <b>Account Vault:</b> Encrypted Session Storage
🛡️ <b>Health Checker:</b> Check Alive / Banned Status
🛠 <b>Utility Tools:</b> Leave Channels, Clean Dialogs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 <i>100% Client-side Encrypted & Highly Secure.</i>
"""

HELP_TEXT = """
📖 <b>𝗛𝗢𝗪 𝗧𝗢 𝗨𝗦𝗘 𝗧𝗛𝗜𝗦 𝗕𝗢𝗧</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣ <b>Generate String Session:</b>
• Click on <code>⚡ Generate Session</code>.
• Select Pyrogram v2 or Telethon.
• Use default API or enter your own API_ID & API_HASH.
• Enter your phone number with country code (e.g. <code>+919876543210</code>).
• Enter the OTP code. 
  <i>Tip: If Telegram blocks OTP delivery, enter code with spaces like <code>1 2 3 4 5</code>.</i>
• If 2FA is enabled, enter your password.
• Your session will be delivered instantly with 1-click copy & save!

2️⃣ <b>Active Devices & Security:</b>
• View all logged-in devices, active IPs, countries, and login dates.
• Click <b>Terminate All Other Sessions</b> to kick out all unknown devices immediately.

3️⃣ <b>Account Vault:</b>
• Store your multiple sessions safely with AES-Fernet encryption.
• Run 1-click Alive/Dead status checks on your accounts.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
