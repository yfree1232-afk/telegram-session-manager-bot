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

START_TEXT = (
    '<tg-emoji emoji-id="5332328182907445859">✨</tg-emoji><tg-emoji emoji-id="5332317716072142654">✨</tg-emoji>\n'
    '<tg-emoji emoji-id="5332269736992481255">✨</tg-emoji><tg-emoji emoji-id="5334580485232302082">✨</tg-emoji><b>ICE SESSION MANAGER</b> <tg-emoji emoji-id="6269464775307038921">🅿️</tg-emoji><tg-emoji emoji-id="6269520996428943568">🔴</tg-emoji><tg-emoji emoji-id="6273972468038242731">🟡</tg-emoji><tg-emoji emoji-id="5415938190999594673">🟢</tg-emoji>\n\n'
    '<tg-emoji emoji-id="5415767770992256042">🕊️</tg-emoji><tg-emoji emoji-id="5415689185975640304">☁️</tg-emoji><tg-emoji emoji-id="5415799536570376505">☁️</tg-emoji><tg-emoji emoji-id="5415799536570376505">☁️</tg-emoji><tg-emoji emoji-id="5418027134243344774">🕉️</tg-emoji><tg-emoji emoji-id="5416127354244213003">🕉️</tg-emoji><tg-emoji emoji-id="5415878933335809773">☁️</tg-emoji><tg-emoji emoji-id="5393566127261516952">☁️</tg-emoji><tg-emoji emoji-id="5390888670418992568">🕊️</tg-emoji>\n'
    '<tg-emoji emoji-id="5391231069506801786">〰️</tg-emoji><tg-emoji emoji-id="5393566127261516952">〰️</tg-emoji><tg-emoji emoji-id="5390888670418992568">〰️</tg-emoji><tg-emoji emoji-id="5391249542161138443">〰️</tg-emoji><tg-emoji emoji-id="5391247665260431980">〰️</tg-emoji><tg-emoji emoji-id="5391231069506801786">〰️</tg-emoji><tg-emoji emoji-id="5393566127261516952">〰️</tg-emoji><tg-emoji emoji-id="5390888670418992568">〰️</tg-emoji><tg-emoji emoji-id="5391249542161138443">〰️</tg-emoji>\n\n'
    '<tg-emoji emoji-id="5409320020058584473">🛡️</tg-emoji> <b>Trusted workspace • 100% safe handling</b>\n'
    '<tg-emoji emoji-id="5415938190999594673">🟢</tg-emoji> <b>Free mode active</b>\n'
    '<tg-emoji emoji-id="5409230963911701228">📥</tg-emoji> <b>Upload <code>.session</code>, <code>.zip</code>, or <code>.json</code> to begin.</b>\n'
    '<tg-emoji emoji-id="5458371041954897946">⚡</tg-emoji> <b>Choose any operation from the menu below:</b>'
)

HELP_TEXT = (
    '<tg-emoji emoji-id="5332328182907445859">✨</tg-emoji> <b>ICE BOT • USER GUIDE</b>\n'
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
    '<tg-emoji emoji-id="5458371041954897946">⚡</tg-emoji> <b>1. Generate String Session:</b>\n'
    '• Choose <b>QR Code Login (Instant - No OTP)</b> or <b>Pyrogram / Telethon</b>.\n'
    '• Enter your phone number with country code (e.g. <code>+919876543210</code>).\n'
    '• Official Telegram notifications (777000) se OTP enter karein.\n\n'
    '<tg-emoji emoji-id="5408905620139028881">🔍</tg-emoji> <b>2. Check Sessions & SpamBot:</b>\n'
    '• Paste any session string or upload <code>.session</code>/<code>.zip</code>.\n'
    '• Live MTProto health check aur @SpamBot restriction status.\n\n'
    '<tg-emoji emoji-id="5409230963911701228">📩</tg-emoji> <b>3. Read Latest OTP:</b>\n'
    '• Official Telegram Chat 777000 se live OTP fetch karein.\n\n'
    '<tg-emoji emoji-id="5408832111773757273">🚨</tg-emoji> <b>4. Terminate All Sessions:</b>\n'
    '• 1-click me sabhi unwanted devices disconnect karein.\n'
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
)
