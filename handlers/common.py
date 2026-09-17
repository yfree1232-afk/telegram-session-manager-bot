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

<blockquote><i>The Ultimate All-in-One Telegram Account & Session Automation Suite inspired by @Oversout_bot.</i></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <b>String Generator:</b> Pyrogram v2 & Telethon (Fast & Safe)
🎙️ <b>VC Auto-DM & Blaster:</b> Real-time listener DMs & Auto-detect
📱 <b>Device Manager:</b> Active IPs, Models & 1-Click Terminate All
👥 <b>Account Vault:</b> Encrypted Cloud Storage & 1-Click ON/OFF
📡 <b>Multi Broadcast:</b> Send announcements across all IDs
🛠️ <b>Utility Tools:</b> Leave all channels, Clear chats & SpamBot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 <b>Database:</b> <i>MongoDB Atlas Cloud (AES-256 Encrypted)</i>
"""

HELP_TEXT = """
📖 <b>𝗛𝗢𝗪 𝗧𝗢 𝗨𝗦𝗘 𝗧𝗛𝗜𝗦 𝗕𝗢𝗧</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣ <b>⚡ Generate String Session:</b>
• Click on <code>⚡ Generate Session</code>.
• Choose <b>Pyrogram (v2)</b> or <b>Telethon</b>.
• Select <i>Default Fast API</i> or your custom API credentials.
• Enter your phone number with country code (e.g. <code>+919876543210</code>).
• Enter OTP with spaces (e.g. <code>1 2 3 4 5</code>) to avoid Telegram blocks.
• Provide 2FA password if enabled. Instant 1-click copy & save to vault!

2️⃣ <b>🎙️ Voice Chat (VC) Auto-DM:</b>
• 1-Click <i>Auto-Detect Live VCs</i> across all groups.
• Customize text (with <code>{name}</code>, <code>{channel}</code>), Voice note, Stickers, or Media.
• Anti-ban dynamic delays (1.5s to 8.0s).
• Auto-skips speakers & hosts to keep accounts safe.

3️⃣ <b>📱 Active Devices & Security:</b>
• Inspect all logged-in devices, IP addresses, countries, and login dates.
• Click <b>Terminate All Other Sessions</b> to kick out all unknown devices immediately!

4️⃣ <b>👥 Account Vault & ON/OFF Toggles:</b>
• Store unlimited accounts with AES-Fernet cloud encryption.
• Use 1-click ON/OFF switches to decide which accounts participate in automation.
• Batch health ping to detect active vs banned accounts.

5️⃣ <b>🛠️ Account Utilities:</b>
• Leave all channels and groups with 1 click.
• Delete all dialogs / clear chat history.
• Check SpamBot / Ban status directly from Telegram!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

