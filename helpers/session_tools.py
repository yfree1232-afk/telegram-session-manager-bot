import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import datetime
from pyrogram import Client, raw
from pyrogram.errors import (
    UserDeactivated, SessionRevoked, AuthKeyUnregistered,
    FloodWait, PasswordHashInvalid, SessionPasswordNeeded
)
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
from telethon.tl.functions.auth import ResetAuthorizationsRequest
from telethon.errors import (
    UserDeactivatedError, SessionRevokedError, AuthKeyUnregisteredError,
    SessionPasswordNeededError
)
from telethon.sessions.string import StringSession, CURRENT_VERSION, _STRUCT_PREFORMAT
import ipaddress
import base64
import struct

def to_telethon_session(session_str: str) -> str:
    """Converts Pyrogram (v2) string or raw session to valid Telethon StringSession."""
    s = session_str.strip()
    if s.startswith("1") and len(s) > 200:
        return s
    try:
        pad = len(s) % 4
        s_padded = s + ("=" * (4 - pad) if pad else "")
        raw_bytes = base64.urlsafe_b64decode(s_padded)
        dc_id, test_mode, auth_key, user_id, is_bot = struct.unpack(">B?256sQ?", raw_bytes[:267])
        dc_ips = {
            1: "149.154.175.50",
            2: "149.154.167.51",
            3: "149.154.175.100",
            4: "149.154.167.91",
            5: "91.108.56.165"
        }
        ip = dc_ips.get(dc_id, "149.154.167.51")
        ip_bytes = ipaddress.ip_address(ip).packed
        data_bytes = struct.pack(_STRUCT_PREFORMAT.format(len(ip_bytes)), dc_id, ip_bytes, 443, auth_key)
        return CURRENT_VERSION + StringSession.encode(data_bytes)
    except Exception:
        return s

def to_pyrogram_session(session_str: str) -> str:
    """Converts Telethon StringSession to valid Pyrogram (v2) session string."""
    s = session_str.strip()
    if not (s.startswith("1") and len(s) > 200):
        return s
    try:
        sess = StringSession(s)
        auth_bytes = sess.auth_key.key
        dc_id = sess.dc_id
        packed = struct.pack(">B?256sQ?", dc_id, False, auth_bytes, 0, False)
        return base64.urlsafe_b64encode(packed).decode().rstrip("=")
    except Exception:
        return s

async def check_session_health(session_str: str, session_type: str = "pyrogram"):
    """
    Check if a string session is alive, banned, or expired.
    Universal adapter supporting both Pyrogram and Telethon formats.
    """
    session_str = session_str.strip()
    result = {
        "status": "dead",
        "user_id": None,
        "name": None,
        "username": None,
        "phone": None,
        "dc_id": None,
        "is_premium": False,
        "error": None
    }

    tel_str = to_telethon_session(session_str)
    client = TelegramClient(StringSession(tel_str), config.API_ID, config.API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            result["error"] = "Session Expired or Unauthorized"
            return result
        me = await client.get_me()
        result["status"] = "alive"
        result["user_id"] = me.id
        result["name"] = f"{me.first_name or ''} {me.last_name or ''}".strip() or "Telegram User"
        result["username"] = me.username or "None"
        result["phone"] = me.phone or "Hidden"
        result["dc_id"] = getattr(client.session, "dc_id", 1)
        result["is_premium"] = getattr(me, "premium", False)
        return result
    except (UserDeactivatedError, SessionRevokedError, AuthKeyUnregisteredError) as e:
        result["error"] = f"Account Banned/Terminated: {type(e).__name__}"
        return result
    except Exception as e:
        result["error"] = str(e)
        return result
    finally:
        if client.is_connected():
            await client.disconnect()

async def get_active_sessions(session_str: str, session_type: str = "telethon"):
    """
    Fetch all active authorizations/devices for a Telegram account.
    Supports both Pyrogram and Telethon session strings.
    """
    sessions_list = []
    session_str = session_str.strip()
    tel_str = to_telethon_session(session_str)
    client = TelegramClient(StringSession(tel_str), config.API_ID, config.API_HASH)
    try:
        await client.connect()
        if await client.is_user_authorized():
            result = await client(GetAuthorizationsRequest())
            for auth in result.authorizations:
                sessions_list.append({
                    "hash": auth.hash,
                    "device_model": auth.device_model,
                    "platform": auth.platform,
                    "system_version": auth.system_version,
                    "app_name": auth.app_name,
                    "app_version": auth.app_version,
                    "date_created": auth.date_created.strftime("%Y-%m-%d %H:%M") if hasattr(auth.date_created, "strftime") else str(auth.date_created),
                    "date_active": auth.date_active.strftime("%Y-%m-%d %H:%M") if hasattr(auth.date_active, "strftime") else str(auth.date_active),
                    "ip": auth.ip,
                    "country": auth.country,
                    "current": getattr(auth, "current", False)
                })
    finally:
        if client.is_connected():
            await client.disconnect()

    return sessions_list

async def terminate_all_sessions(session_str: str, session_type: str = "telethon"):
    """
    Terminates all active authorizations except the current one.
    Supports both Pyrogram and Telethon session strings.
    """
    session_str = session_str.strip()
    tel_str = to_telethon_session(session_str)
    client = TelegramClient(StringSession(tel_str), config.API_ID, config.API_HASH)
    try:
        await client.connect()
        await client(ResetAuthorizationsRequest())
        return True, "All other sessions have been successfully terminated! 🚀"
    except Exception as e:
        return False, str(e)
    finally:
        if client.is_connected():
            await client.disconnect()

async def terminate_single_session(session_str: str, session_type: str, auth_hash: int):
    """
    Terminates a specific authorization by its hash.
    Supports both Pyrogram and Telethon session strings.
    """
    session_str = session_str.strip()
    tel_str = to_telethon_session(session_str)
    client = TelegramClient(StringSession(tel_str), config.API_ID, config.API_HASH)
    try:
        await client.connect()
        await client(ResetAuthorizationRequest(hash=int(auth_hash)))
        return True, "Session terminated successfully! 🗑️"
    except Exception as e:
        return False, str(e)
    finally:
        if client.is_connected():
            await client.disconnect()

async def leave_all_dialogs(session_str: str, session_type: str = "telethon"):
    """
    Leave all non-owned channels and supergroups.
    Supports both Pyrogram and Telethon session strings.
    """
    left_count = 0
    errors = 0
    session_str = session_str.strip()
    tel_str = to_telethon_session(session_str)
    client = TelegramClient(StringSession(tel_str), config.API_ID, config.API_HASH)
    try:
        await client.connect()
        from telethon.tl.functions.channels import LeaveChannelRequest
        async for dialog in client.iter_dialogs():
            if dialog.is_channel or dialog.is_group:
                try:
                    await client(LeaveChannelRequest(dialog.input_entity))
                    left_count += 1
                except Exception:
                    errors += 1
        return True, f"Successfully left {left_count} channels/groups! (Skipped/Errors: {errors})"
    except Exception as e:
        return False, str(e)
    finally:
        if client.is_connected():
            await client.disconnect()

async def check_spambot_status(session_str: str, session_type: str = "telethon"):
    """
    Check if the account is limited or banned by sending /start to @SpamBot.
    Supports both Pyrogram and Telethon session strings.
    """
    session_str = session_str.strip()
    tel_str = to_telethon_session(session_str)
    client = TelegramClient(StringSession(tel_str), config.API_ID, config.API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False, "Session Unauthorized or Expired"

        # Send /start to SpamBot
        spambot = await client.get_entity("SpamBot")
        await client.send_message(spambot, "/start")
        await asyncio.sleep(2.5)

        # Get last message from SpamBot
        messages = await client.get_messages(spambot, limit=1)
        if messages and messages[0].text:
            text = messages[0].text
            is_clean = "good news" in text.lower() or "no limits" in text.lower()
            return True, {
                "clean": is_clean,
                "message": text
            }
        else:
            return True, {
                "clean": True,
                "message": "No response from @SpamBot (Account likely clean)"
            }
    except Exception as e:
        return False, str(e)
    finally:
        if client.is_connected():
            await client.disconnect()

async def delete_all_dialogs(session_str: str, session_type: str = "telethon"):
    """
    Delete all private chats / dialogs from the account.
    Supports both Pyrogram and Telethon session strings.
    """
    deleted_count = 0
    session_str = session_str.strip()
    tel_str = to_telethon_session(session_str)
    client = TelegramClient(StringSession(tel_str), config.API_ID, config.API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False, "Session Unauthorized or Expired"

        async for dialog in client.iter_dialogs():
            if dialog.is_user and not dialog.entity.is_self:
                try:
                    await client.delete_dialog(dialog.entity)
                    deleted_count += 1
                except Exception:
                    pass
        return True, f"Successfully cleared {deleted_count} private dialogs & chats!"
    except Exception as e:
        return False, str(e)
    finally:
        if client.is_connected():
            await client.disconnect()

async def check_2fa_status(session_str: str, session_type: str = "telethon"):
    """
    Checks if Two-Step Verification (2FA) is active on the account.
    Returns details on 2FA status, hint, and recovery email presence.
    Supports both Pyrogram and Telethon session strings.
    """
    session_str = session_str.strip()
    tel_str = to_telethon_session(session_str)
    client = TelegramClient(StringSession(tel_str), config.API_ID, config.API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False, "Session Unauthorized or Expired"

        from telethon.tl.functions.account import GetPasswordRequest
        pwd_info = await client(GetPasswordRequest())
        has_pwd = bool(getattr(pwd_info, "has_password", False))
        hint = getattr(pwd_info, "hint", None)
        has_rec = bool(getattr(pwd_info, "has_recovery", False))
        email_pattern = getattr(pwd_info, "email_unconfirmed_pattern", None)

        return True, {
            "has_2fa": has_pwd,
            "hint": hint if has_pwd else None,
            "has_recovery": has_rec,
            "email_pattern": email_pattern
        }
    except Exception as e:
        return False, str(e)
    finally:
        if client.is_connected():
            await client.disconnect()

async def get_account_full_info(session_str: str, session_type: str = "telethon"):
    """
    Fetches comprehensive account details: Profile, DC, Security, Stats.
    Supports both Pyrogram and Telethon session strings.
    """
    session_str = session_str.strip()
    tel_str = to_telethon_session(session_str)
    client = TelegramClient(StringSession(tel_str), config.API_ID, config.API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False, "Session Unauthorized or Expired"

        me = await client.get_me()
        user_id = me.id
        name = f"{me.first_name or ''} {me.last_name or ''}".strip()
        username = me.username or "None"
        phone = me.phone or "Hidden"
        is_premium = bool(getattr(me, "premium", False))
        is_verified = bool(getattr(me, "verified", False))
        is_restricted = bool(getattr(me, "restricted", False))
        is_scam = bool(getattr(me, "scam", False))
        is_fake = bool(getattr(me, "fake", False))

        # Check 2FA
        from telethon.tl.functions.account import GetPasswordRequest
        has_2fa = False
        try:
            pwd = await client(GetPasswordRequest())
            has_2fa = bool(getattr(pwd, "has_password", False))
        except Exception:
            pass

        # Check Active Devices Count
        active_sessions = 1
        try:
            auths = await client(GetAuthorizationsRequest())
            active_sessions = len(auths.authorizations)
        except Exception:
            pass

        # Count Dialogs & Channels
        dialog_cnt = 0
        channel_cnt = 0
        try:
            async for d in client.iter_dialogs(limit=100):
                dialog_cnt += 1
                if d.is_channel or d.is_group:
                    channel_cnt += 1
        except Exception:
            pass

        dc_id = getattr(client.session, "dc_id", "Unknown")

        return True, {
            "user_id": user_id,
            "name": name,
            "username": username,
            "phone": phone,
            "dc_id": dc_id,
            "is_premium": is_premium,
            "is_verified": is_verified,
            "is_restricted": is_restricted,
            "is_scam": is_scam,
            "is_fake": is_fake,
            "has_2fa": has_2fa,
            "active_sessions": active_sessions,
            "dialogs_count": dialog_cnt,
            "channels_count": channel_cnt
        }
    except Exception as e:
        return False, str(e)
    finally:
        if client.is_connected():
            await client.disconnect()

# =========================================================================
# 📱 DEVICE FINGERPRINTS / CLONER SUITE
# =========================================================================

DEVICE_FINGERPRINTS = {
    "samsung": {
        "name": "Samsung Galaxy S24 Ultra",
        "icon": "📱",
        "device_model": "Samsung Galaxy S24 Ultra",
        "system_version": "Android 14 (One UI 6.1)",
        "app_version": "10.14.0",
        "lang_code": "en",
        "system_lang_code": "en-US"
    },
    "iphone": {
        "name": "Apple iPhone 15 Pro Max",
        "icon": "🍏",
        "device_model": "iPhone 15 Pro Max",
        "system_version": "iOS 17.5.1",
        "app_version": "10.14.1",
        "lang_code": "en",
        "system_lang_code": "en-US"
    },
    "xiaomi": {
        "name": "Xiaomi 14 Pro",
        "icon": "📱",
        "device_model": "Xiaomi 14 Pro",
        "system_version": "Android 14 (HyperOS)",
        "app_version": "10.14.0",
        "lang_code": "en",
        "system_lang_code": "en-US"
    },
    "desktop": {
        "name": "Windows 11 PC (64-bit)",
        "icon": "💻",
        "device_model": "Desktop PC x64",
        "system_version": "Windows 11 Pro 23H2",
        "app_version": "5.1.5 x64",
        "lang_code": "en",
        "system_lang_code": "en-US"
    },
    "macos": {
        "name": "Apple MacBook Pro M3",
        "icon": "🍎",
        "device_model": "MacBook Pro M3",
        "system_version": "macOS Sonoma 14.5",
        "app_version": "10.14.2",
        "lang_code": "en",
        "system_lang_code": "en-US"
    },
    "default": {
        "name": "Official Telegram App",
        "icon": "⚡",
        "device_model": "Official Telegram App",
        "system_version": "14.0",
        "app_version": "10.14.0",
        "lang_code": "en",
        "system_lang_code": "en-US"
    }
}

# =========================================================================
# 📅 ACCOUNT REGISTRATION AGE ESTIMATOR
# =========================================================================

def estimate_account_age(user_id: int) -> dict:
    milestones = [
        (100_000_000, "2013 - 2015", "Pioneer (Early Telegram)", "💎 Ultra Rare"),
        (250_000_000, "2016", "Veteran (8+ years old)", "⭐️ High Value"),
        (450_000_000, "2017", "Established (7+ years old)", "⭐️ High Value"),
        (750_000_000, "2018", "Established (6+ years old)", "✨ Rare"),
        (1_050_000_000, "2019", "Regular (5+ years old)", "✨ Rare"),
        (1_550_000_000, "2020", "Covid-Era (4+ years old)", "🟢 Established"),
        (2_100_000_000, "2021", "Active (3+ years old)", "🟢 Established"),
        (5_300_000_000, "2022 - 2023", "Modern (1-2 years old)", "⚪️ Normal"),
        (6_900_000_000, "2023 - 2024", "Recent Account", "⚪️ Normal"),
        (9_999_999_999, "2024 - 2026", "Fresh / New Account", "🆕 Fresh")
    ]
    for limit, period, desc, rarity in milestones:
        if user_id <= limit:
            return {
                "user_id": user_id,
                "period": period,
                "description": desc,
                "rarity": rarity
            }
    return {
        "user_id": user_id,
        "period": "2024 - 2026",
        "description": "Fresh Account",
        "rarity": "🆕 Fresh"
    }

# =========================================================================
# 👁️ ACCOUNT PRIVACY SETTINGS AUDIT
# =========================================================================

async def check_account_privacy(session_str: str):
    session_str = session_str.strip()
    tel_str = to_telethon_session(session_str)
    client = TelegramClient(StringSession(tel_str), config.API_ID, config.API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False, "Session Unauthorized or Expired"

        from telethon.tl.functions.account import GetPrivacyRequest
        from telethon.tl.types import (
            InputPrivacyKeyPhoneNumber, InputPrivacyKeyStatusTimestamp,
            InputPrivacyKeyProfilePhoto, PrivacyValueAllowAll,
            PrivacyValueAllowContacts, PrivacyValueDisallowAll
        )

        def parse_rule(rules):
            for r in rules:
                if isinstance(r, PrivacyValueDisallowAll):
                    return "🔒 Nobody (Hidden)"
                elif isinstance(r, PrivacyValueAllowContacts):
                    return "👥 My Contacts Only"
                elif isinstance(r, PrivacyValueAllowAll):
                    return "🌐 Everybody (Public)"
            return "🔒 Protected"

        phone_res = await client(GetPrivacyRequest(key=InputPrivacyKeyPhoneNumber()))
        last_seen_res = await client(GetPrivacyRequest(key=InputPrivacyKeyStatusTimestamp()))
        photo_res = await client(GetPrivacyRequest(key=InputPrivacyKeyProfilePhoto()))

        return True, {
            "phone_privacy": parse_rule(phone_res.rules),
            "last_seen_privacy": parse_rule(last_seen_res.rules),
            "photo_privacy": parse_rule(photo_res.rules)
        }
    except Exception as e:
        return False, str(e)
    finally:
        if client.is_connected():
            await client.disconnect()

# =========================================================================
# 🔀 SESSION FORMAT CONVERTER
# =========================================================================

async def convert_session(session_str: str):
    session_str = session_str.strip()
    from handlers.common import detect_session_type
    current_type = detect_session_type(session_str)

    if current_type == "telethon":
        pyro_string = to_pyrogram_session(session_str)
        health = await check_session_health(session_str, "telethon")
        return True, {
            "from_type": "TELETHON",
            "to_type": "PYROGRAM (v2)",
            "result": pyro_string,
            "user": health.get("name", "Telegram User"),
            "phone": health.get("phone", "N/A")
        }
    else:
        telethon_string = to_telethon_session(session_str)
        health = await check_session_health(session_str, "pyrogram")
        return True, {
            "from_type": "PYROGRAM (v2)",
            "to_type": "TELETHON",
            "result": telethon_string,
            "user": health.get("name", "Telegram User"),
            "phone": health.get("phone", "N/A")
        }

# =========================================================================
# 📩 READ OTP (TELEGRAM OFFICIAL 777000 NOTIFICATIONS)
# =========================================================================

async def read_latest_otp(session_str: str, session_type: str = "telethon"):
    """Fetch the latest login OTP sent to the account by Telegram (from 777000)."""
    session_str = session_str.strip()
    tel_str = to_telethon_session(session_str)
    client = TelegramClient(StringSession(tel_str), config.API_ID, config.API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False, "Session is expired or invalid."

        me = await client.get_me()
        otp_found = None
        full_msg = None
        msg_date = None

        async for msg in client.iter_messages(777000, limit=5):
            if msg.text:
                full_msg = msg.text
                msg_date = msg.date.strftime("%Y-%m-%d %H:%M:%S UTC") if msg.date else "Recent"
                import re
                matches = re.findall(r'\b\d{5,6}\b', msg.text)
                if matches:
                    otp_found = matches[0]
                    break
                elif "code" in msg.text.lower():
                    otp_found = msg.text
                    break

        if not full_msg:
            return True, {
                "user": me.first_name,
                "phone": me.phone or "N/A",
                "otp": "No recent OTP found",
                "text": "No messages received from Telegram Service Notifications (777000) recently.",
                "date": "N/A"
            }

        return True, {
            "user": me.first_name,
            "phone": me.phone or "N/A",
            "otp": otp_found or "See message text",
            "text": full_msg,
            "date": msg_date
        }
    except Exception as e:
        return False, str(e)
    finally:
        if client.is_connected():
            await client.disconnect()

# =========================================================================
# 📇 CONTACT TOOL (COUNT & CLEANUP)
# =========================================================================

async def manage_contacts(session_str: str, action: str = "count"):
    session_str = session_str.strip()
    tel_str = to_telethon_session(session_str)
    client = TelegramClient(StringSession(tel_str), config.API_ID, config.API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False, "Session is expired or invalid."

        from telethon.tl.functions.contacts import GetContactsRequest, DeleteContactsRequest
        res = await client(GetContactsRequest(hash=0))
        contacts = getattr(res, "contacts", [])
        cnt = len(contacts)

        if action == "delete" and cnt > 0:
            user_ids = [c.user_id for c in contacts]
            await client(DeleteContactsRequest(id=user_ids))
            return True, f"Successfully deleted {cnt} contacts!"

        return True, {"count": cnt}
    except Exception as e:
        return False, str(e)
    finally:
        if client.is_connected():
            await client.disconnect()

# =========================================================================
# 📦 FILE PARSER & ZIP EXTRACTION HELPERS
# =========================================================================

import sqlite3
import tempfile
import os
import io
import zipfile
import json
import base64
import struct
import ipaddress

def parse_session_file(filename: str, raw_bytes: bytes) -> tuple:
    """
    Parses a session file from raw bytes.
    Supports:
    1. Plain text session string (.txt, .session text)
    2. JSON format with 'session' or 'session_string' (.json)
    3. Telethon SQLite database (.session binary)
    4. Pyrogram SQLite database (.session binary)
    Returns: (session_string, session_type, metadata_dict)
    """
    from handlers.common import detect_session_type
    
    # 1. Try plain text / json
    try:
        text = raw_bytes.decode("utf-8", errors="ignore").strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                data = json.loads(text)
                for k in ["session", "session_string", "string_session", "telethon", "pyrogram"]:
                    if k in data and isinstance(data[k], str) and len(data[k]) > 40:
                        stype = detect_session_type(data[k])
                        return data[k], stype, data
            except Exception:
                pass
        if len(text) > 50 and not text.startswith("SQLite"):
            lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 50]
            if lines:
                return lines[0], detect_session_type(lines[0]), {}
    except Exception:
        pass

    # 2. Try SQLite format
    if raw_bytes.startswith(b"SQLite format 3"):
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".session", delete=False) as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name

            conn = sqlite3.connect(tmp_path)
            cursor = conn.cursor()

            # Try Pyrogram schema: sessions(dc_id, test_mode, auth_key, date, user_id, is_bot)
            try:
                cursor.execute("SELECT dc_id, test_mode, auth_key, date, user_id, is_bot FROM sessions")
                row = cursor.fetchone()
                if row and row[2]:
                    dc_id, test_mode, auth_key, date, user_id, is_bot = row
                    packed = struct.pack(">B?256sQ?", dc_id, bool(test_mode), auth_key, user_id, bool(is_bot))
                    s_str = base64.urlsafe_b64encode(packed).decode().rstrip("=")
                    conn.close()
                    os.unlink(tmp_path)
                    return s_str, "pyrogram", {"user_id": user_id, "dc_id": dc_id}
            except Exception:
                pass

            # Try Telethon schema: sessions(dc_id, server_address, port, auth_key)
            try:
                cursor.execute("SELECT dc_id, server_address, port, auth_key FROM sessions")
                row = cursor.fetchone()
                if row and row[3]:
                    dc_id, ip, port, auth_key = row
                    ip_packed = ipaddress.ip_address(ip).packed if ip else b"\x00\x00\x00\x00"
                    data = struct.pack(">B4sH256s", dc_id, ip_packed, port or 443, auth_key)
                    s_str = "1" + base64.urlsafe_b64encode(data).decode().rstrip("=")
                    conn.close()
                    os.unlink(tmp_path)
                    return s_str, "telethon", {"dc_id": dc_id, "ip": ip}
            except Exception:
                pass

            conn.close()
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    return None, "unknown", {}

def extract_all_sessions_from_bytes(filename: str, raw_bytes: bytes) -> list:
    """
    Extracts all sessions from a file or zip archive.
    Returns list of dicts: [{"filename": ..., "session": ..., "type": ..., "meta": ...}]
    """
    from handlers.common import detect_session_type
    results = []
    
    if filename.lower().endswith(".zip") or raw_bytes.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
                for fname in z.namelist():
                    if fname.endswith("/") or "__MACOSX" in fname:
                        continue
                    b = z.read(fname)
                    s_str, stype, meta = parse_session_file(fname, b)
                    if s_str:
                        results.append({
                            "filename": fname,
                            "session": s_str,
                            "type": stype,
                            "meta": meta
                        })
        except Exception:
            pass
        return results

    # If txt, check for multiple lines
    try:
        text = raw_bytes.decode("utf-8", errors="ignore").strip()
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 50]
        if len(lines) > 1:
            for idx, line in enumerate(lines, 1):
                stype = detect_session_type(line)
                results.append({
                    "filename": f"session_{idx}.txt",
                    "session": line,
                    "type": stype,
                    "meta": {}
                })
            return results
    except Exception:
        pass

    s_str, stype, meta = parse_session_file(filename, raw_bytes)
    if s_str:
        results.append({
            "filename": filename,
            "session": s_str,
            "type": stype,
            "meta": meta
        })
    return results

def create_zip_archive(files_dict: dict) -> bytes:
    """Creates a zip archive in memory from a dict of {filename: content}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fname, content in files_dict.items():
            if isinstance(content, str):
                z.writestr(fname, content.encode("utf-8"))
            else:
                z.writestr(fname, content)
    return buf.getvalue()




