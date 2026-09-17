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
import config

async def check_session_health(session_str: str, session_type: str = "pyrogram"):
    """
    Check if a string session is alive, banned, or expired.
    Returns a dict with health details.
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

    if session_type.lower() == "pyrogram":
        client = Client(
            name="temp_check",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_str,
            in_memory=True
        )
        try:
            await client.connect()
            me = await client.get_me()
            result["status"] = "alive"
            result["user_id"] = me.id
            result["name"] = f"{me.first_name or ''} {me.last_name or ''}".strip()
            result["username"] = me.username
            result["phone"] = me.phone_number
            result["dc_id"] = me.dc_id
            result["is_premium"] = getattr(me, "is_premium", False)
            await client.disconnect()
        except (UserDeactivated, SessionRevoked, AuthKeyUnregistered) as e:
            result["error"] = f"Account Banned/Terminated: {type(e).__name__}"
        except Exception as e:
            result["error"] = str(e)
        finally:
            if client.is_connected:
                await client.disconnect()

    else: # Telethon
        client = TelegramClient(StringSession(session_str), config.API_ID, config.API_HASH)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                result["error"] = "Session Expired or Unauthorized"
                return result
            me = await client.get_me()
            result["status"] = "alive"
            result["user_id"] = me.id
            result["name"] = f"{me.first_name or ''} {me.last_name or ''}".strip()
            result["username"] = me.username
            result["phone"] = me.phone
            result["is_premium"] = getattr(me, "premium", False)
            await client.disconnect()
        except (UserDeactivatedError, SessionRevokedError, AuthKeyUnregisteredError) as e:
            result["error"] = f"Account Banned/Terminated: {type(e).__name__}"
        except Exception as e:
            result["error"] = str(e)
        finally:
            if client.is_connected():
                await client.disconnect()

    return result

async def get_active_sessions(session_str: str, session_type: str = "pyrogram"):
    """
    Fetch all active authorizations/devices for a Telegram account.
    """
    sessions_list = []
    session_str = session_str.strip()

    if session_type.lower() == "pyrogram":
        client = Client(
            name="temp_auth",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_str,
            in_memory=True
        )
        try:
            await client.connect()
            auths = await client.invoke(raw.functions.account.GetAuthorizations())
            for auth in auths.authorizations:
                sessions_list.append({
                    "hash": auth.hash,
                    "device_model": auth.device_model,
                    "platform": auth.platform,
                    "system_version": auth.system_version,
                    "app_name": auth.app_name,
                    "app_version": auth.app_version,
                    "date_created": datetime.datetime.fromtimestamp(auth.date_created).strftime("%Y-%m-%d %H:%M"),
                    "date_active": datetime.datetime.fromtimestamp(auth.date_active).strftime("%Y-%m-%d %H:%M"),
                    "ip": auth.ip,
                    "country": auth.country,
                    "current": getattr(auth, "current", False) or getattr(auth, "is_current", False)
                })
        finally:
            if client.is_connected:
                await client.disconnect()

    else: # Telethon
        client = TelegramClient(StringSession(session_str), config.API_ID, config.API_HASH)
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

async def terminate_all_sessions(session_str: str, session_type: str = "pyrogram"):
    """
    Terminates all active authorizations except the current one.
    """
    session_str = session_str.strip()
    if session_type.lower() == "pyrogram":
        client = Client(
            name="temp_term",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_str,
            in_memory=True
        )
        try:
            await client.connect()
            await client.invoke(raw.functions.account.ResetAuthorizations())
            return True, "All other sessions have been successfully terminated! 🚀"
        except Exception as e:
            return False, str(e)
        finally:
            if client.is_connected:
                await client.disconnect()

    else: # Telethon
        client = TelegramClient(StringSession(session_str), config.API_ID, config.API_HASH)
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
    """
    session_str = session_str.strip()
    if session_type.lower() == "pyrogram":
        client = Client(
            name="temp_single_term",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_str,
            in_memory=True
        )
        try:
            await client.connect()
            await client.invoke(raw.functions.account.ResetAuthorization(hash=int(auth_hash)))
            return True, "Session terminated successfully! 🗑️"
        except Exception as e:
            return False, str(e)
        finally:
            if client.is_connected:
                await client.disconnect()
    else:
        client = TelegramClient(StringSession(session_str), config.API_ID, config.API_HASH)
        try:
            await client.connect()
            await client(ResetAuthorizationRequest(hash=int(auth_hash)))
            return True, "Session terminated successfully! 🗑️"
        except Exception as e:
            return False, str(e)
        finally:
            if client.is_connected():
                await client.disconnect()

async def leave_all_dialogs(session_str: str, session_type: str = "pyrogram"):
    """
    Leave all non-owned channels and supergroups.
    """
    left_count = 0
    errors = 0
    session_str = session_str.strip()

    if session_type.lower() == "pyrogram":
        client = Client(
            name="temp_cleaner",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_str,
            in_memory=True
        )
        try:
            await client.connect()
            async for dialog in client.get_dialogs():
                chat = dialog.chat
                if chat.type.value in ["channel", "supergroup", "group"]:
                    try:
                        await client.leave_chat(chat.id)
                        left_count += 1
                    except Exception:
                        errors += 1
            return True, f"Successfully left {left_count} channels/groups! (Skipped/Errors: {errors})"
        except Exception as e:
            return False, str(e)
        finally:
            if client.is_connected:
                await client.disconnect()
    else:
        client = TelegramClient(StringSession(session_str), config.API_ID, config.API_HASH)
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
