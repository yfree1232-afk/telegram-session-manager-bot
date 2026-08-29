import os
import re
import io
import zipfile
import tempfile
import sqlite3
import asyncio
import logging
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession, SQLiteSession
from telethon.errors import (
    FloodWaitError,
    UserDeactivatedError,
    AuthKeyUnregisteredError,
    AuthKeyDuplicatedError,
    SessionPasswordNeededError,
    UserAlreadyParticipantError,
    InviteRequestSentError,
    InviteHashExpiredError,
    InviteHashInvalidError,
    ChannelsTooMuchError,
    ChannelPrivateError,
    ChannelInvalidError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
    MessageIdInvalidError
)
from config import API_ID, API_HASH
import database

logger = logging.getLogger("SessionManager")

# In-memory dictionary for active Telethon clients: {"{owner_id}_{account_id}": TelegramClient}
active_clients: dict[str, TelegramClient] = {}

def get_client_key(owner_id: int, account_id: int) -> str:
    return f"{owner_id}_{account_id}"

def create_auth_client(session_str: str | None = None) -> TelegramClient:
    """Create Telethon client with realistic Desktop fingerprint."""
    return TelegramClient(
        session=StringSession(session_str) if session_str else StringSession(),
        api_id=API_ID,
        api_hash=API_HASH,
        device_model="Telegram Desktop",
        system_version="Windows 11 x64",
        app_version="5.4.1 x64",
        lang_code="en",
        system_lang_code="en-US"
    )

def parse_telegram_channel_link(link: str) -> tuple[str, str]:
    """Parse Channel / Group link."""
    clean = link.strip()
    clean = re.sub(r'^(https?://)?(www\.)?(t\.me/|telegram\.me/)', '', clean, flags=re.IGNORECASE)
    
    if clean.startswith('+'):
        return 'private', clean[1:].split('?')[0]
    elif clean.lower().startswith('joinchat/'):
        return 'private', clean[9:].split('?')[0]
    elif '+' in clean:
        return 'private', clean.split('+')[-1].split('?')[0]
    elif 'joinchat/' in clean.lower():
        idx = clean.lower().find('joinchat/')
        return 'private', clean[idx+9:].split('?')[0]
    else:
        username = clean.lstrip('@').split('/')[0].split('?')[0]
        return 'public', username

def parse_message_link(link: str) -> tuple[str | int | None, int | None]:
    """
    Extracts (peer, msg_id) from message links:
    - https://t.me/mychannel/123 -> ('mychannel', 123)
    - https://t.me/c/1234567890/123 -> (-1001234567890, 123)
    - @mychannel 123 -> ('mychannel', 123)
    """
    clean = link.strip()
    
    # Check for private channel message format: t.me/c/1234567890/456
    m_c = re.search(r't\.me/c/(\d+)/(\d+)', clean, re.IGNORECASE)
    if m_c:
        raw_id = m_c.group(1)
        msg_id = int(m_c.group(2))
        full_peer = int(f"-100{raw_id}")
        return full_peer, msg_id

    # Check for public channel message format: t.me/mychannel/456
    m_pub = re.search(r't\.me/([a-zA-Z0-9_]+)/(\d+)', clean, re.IGNORECASE)
    if m_pub:
        return m_pub.group(1), int(m_pub.group(2))

    # Check for "@mychannel 123" or "mychannel 123"
    parts = clean.split()
    if len(parts) == 2 and parts[1].isdigit():
        peer = parts[0].lstrip('@')
        if peer.startswith("-100") and peer[4:].isdigit():
            return int(peer), int(parts[1])
        elif peer.isdigit():
            return int(f"-100{peer}"), int(parts[1])
        return peer, int(parts[1])

    return None, None

async def verify_and_extract_session_details(session_str: str) -> tuple[bool, dict | None, str | None]:
    client = create_auth_client(session_str)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, None, "Session is not authorized or expired."
        
        me = await client.get_me()
        dc_id = client.session.dc_id
        details = {
            "account_id": me.id,
            "first_name": me.first_name or "",
            "last_name": me.last_name or "",
            "username": me.username or "",
            "phone_number": f"+{me.phone}" if me.phone else f"ID:{me.id}",
            "dc_id": dc_id
        }
        await client.disconnect()
        return True, details, None
    except Exception as e:
        logger.error(f"Failed to verify session string: {e}")
        return False, None, str(e)

async def start_session(owner_id: int, account_id: int, session_str: str) -> tuple[bool, str]:
    key = get_client_key(owner_id, account_id)
    if key in active_clients:
        await stop_session(owner_id, account_id)

    client = create_auth_client(session_str)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            await database.update_session_health(owner_id, account_id, is_active=False, status_note="Unauthorized / Expired")
            return False, "Session is unauthorized or expired."

        active_clients[key] = client
        logger.info(f"🚀 Started active Telethon client for [{key}]")
        return True, "Session connected successfully."
    except FloodWaitError as e:
        logger.warning(f"⚠️ FloodWait ({e.seconds}s) on starting session {key}")
        await database.update_session_health(owner_id, account_id, is_active=False, status_note=f"FloodWait {e.seconds}s")
        return False, f"FloodWait: {e.seconds} seconds"
    except (AuthKeyUnregisteredError, UserDeactivatedError) as ae:
        logger.warning(f"❌ Session revoked/banned for {key}: {ae}")
        await database.update_session_health(owner_id, account_id, is_active=False, status_note="Revoked / Banned")
        return False, f"Revoked/Banned: {ae}"
    except Exception as e:
        logger.error(f"❌ Failed to start session {key}: {e}", exc_info=True)
        return False, str(e)

async def stop_session(owner_id: int, account_id: int):
    key = get_client_key(owner_id, account_id)
    client = active_clients.pop(key, None)
    if client:
        try:
            if client.is_connected():
                await client.disconnect()
            logger.info(f"🛑 Disconnected session [{key}]")
        except Exception as e:
            logger.warning(f"Error while disconnecting session {key}: {e}")

async def check_session_health(owner_id: int, account_id: int) -> dict:
    key = get_client_key(owner_id, account_id)
    client = active_clients.get(key)
    
    if not client or not client.is_connected():
        sess_data = await database.get_session(owner_id, account_id)
        if not sess_data:
            return {"status": "NOT_FOUND", "message": "Session record not found"}
        
        ok, details, err = await verify_and_extract_session_details(sess_data["session_string"])
        if ok:
            if sess_data.get("is_active", 1):
                await start_session(owner_id, account_id, sess_data["session_string"])
            return {"status": "HEALTHY", "message": "Session valid and reachable", "details": details}
        else:
            await database.update_session_health(owner_id, account_id, is_active=False, status_note=err or "Invalid")
            return {"status": "FAILED", "message": err or "Verification failed"}

    try:
        me = await client.get_me()
        return {
            "status": "HEALTHY",
            "message": "Session active and online in memory",
            "details": {
                "account_id": me.id,
                "first_name": me.first_name,
                "username": me.username,
                "phone": me.phone
            }
        }
    except Exception as e:
        logger.error(f"Health check failed on live client {key}: {e}")
        await database.update_session_health(owner_id, account_id, is_active=False, status_note=str(e))
        return {"status": "FAILED", "message": str(e)}

async def join_channel_single_session(client: TelegramClient, link: str) -> dict:
    if not client.is_connected():
        try:
            await client.connect()
        except Exception as e:
            return {"status": "ERROR", "icon": "🔴", "note": f"Connect Failed: {e}"}

    link_type, target_val = parse_telegram_channel_link(link)
    
    try:
        if link_type == "private":
            res = await client(functions.messages.ImportChatInviteRequest(hash=target_val))
            title = "Private Chat"
            if hasattr(res, "chats") and res.chats:
                title = getattr(res.chats[0], "title", "Private Chat")
            return {"status": "SUCCESS", "icon": "🟢", "note": f"Joined [{title}] ✅"}
        else:
            entity = await client.get_entity(target_val)
            title = getattr(entity, "title", target_val)
            await client(functions.channels.JoinChannelRequest(channel=entity))
            return {"status": "SUCCESS", "icon": "🟢", "note": f"Joined [{title}] ✅"}

    except UserAlreadyParticipantError:
        return {"status": "ALREADY_MEMBER", "icon": "🟢", "note": "Already Joined ℹ️"}
    except InviteRequestSentError:
        return {"status": "REQUEST_SENT", "icon": "🟡", "note": "Join Request Sent (Pending Approval) ⏳"}
    except (InviteHashExpiredError, InviteHashInvalidError):
        return {"status": "INVALID_LINK", "icon": "🔴", "note": "Invite link expired/invalid ❌"}
    except (UsernameInvalidError, UsernameNotOccupiedError):
        return {"status": "INVALID_LINK", "icon": "🔴", "note": "Public username not found ❌"}
    except ChannelsTooMuchError:
        return {"status": "LIMIT_REACHED", "icon": "🔴", "note": "Channel Limit Reached (Max 500) ⚠️"}
    except ChannelPrivateError:
        return {"status": "FORBIDDEN", "icon": "🔴", "note": "Channel is private/banned for this account ⚠️"}
    except FloodWaitError as fe:
        return {"status": "FLOOD_WAIT", "icon": "⏳", "note": f"FloodWait ({fe.seconds}s) ⚠️"}
    except Exception as e:
        err_msg = str(e)
        if "already a participant" in err_msg.lower():
            return {"status": "ALREADY_MEMBER", "icon": "🟢", "note": "Already Joined ℹ️"}
        if "request to join" in err_msg.lower():
            return {"status": "REQUEST_SENT", "icon": "🟡", "note": "Join Request Sent ⏳"}
        logger.error(f"Error in join_channel_single_session: {e}")
        return {"status": "ERROR", "icon": "🔴", "note": f"Failed: {err_msg[:35]}"}

# ----------------- Message Multi-Tool Functions -----------------

async def fetch_message_preview(client: TelegramClient, peer, msg_id: int) -> dict:
    """Fetch metadata and preview of a specific message/post."""
    if not client.is_connected():
        try:
            await client.connect()
        except Exception as e:
            return {"found": False, "error": f"Client connection failed: {e}"}

    try:
        entity = await client.get_entity(peer)
        msgs = await client.get_messages(entity, ids=msg_id)
        if not msgs:
            return {"found": False, "error": "Message not found or deleted."}

        msg = msgs if not isinstance(msgs, list) else msgs[0]
        if not msg:
            return {"found": False, "error": "Message not found or deleted."}

        text = msg.text or msg.raw_text or "[Media Content without caption]"
        title = getattr(entity, "title", str(peer))
        username = getattr(entity, "username", None)
        views = getattr(msg, "views", 0)
        forwards = getattr(msg, "forwards", 0)
        has_media = bool(msg.media)
        
        # Link construction
        if username:
            direct_link = f"https://t.me/{username}/{msg_id}"
        else:
            raw_id = str(getattr(entity, "id", "")).replace("-100", "")
            direct_link = f"https://t.me/c/{raw_id}/{msg_id}"

        return {
            "found": True,
            "title": title,
            "username": f"@{username}" if username else "Private",
            "text": text,
            "views": views,
            "forwards": forwards,
            "has_media": has_media,
            "direct_link": direct_link,
            "peer": peer,
            "msg_id": msg_id
        }
    except Exception as e:
        logger.error(f"Error fetching message preview: {e}")
        return {"found": False, "error": str(e)}

async def react_to_message_single_session(client: TelegramClient, peer, msg_id: int, emoji: str) -> dict:
    """Send an emoji reaction to a message/post."""
    if not client.is_connected():
        try:
            await client.connect()
        except Exception as e:
            return {"status": "ERROR", "icon": "🔴", "note": f"Connect Failed: {e}"}

    try:
        entity = await client.get_entity(peer)
        await client(functions.messages.SendReactionRequest(
            peer=entity,
            msg_id=msg_id,
            reaction=[types.ReactionEmoji(emoticon=emoji)]
        ))
        return {"status": "SUCCESS", "icon": "🟢", "note": f"Reacted with {emoji} ✅"}
    except FloodWaitError as fe:
        return {"status": "FLOOD_WAIT", "icon": "⏳", "note": f"FloodWait ({fe.seconds}s) ⚠️"}
    except Exception as e:
        return {"status": "ERROR", "icon": "🔴", "note": f"Failed: {str(e)[:30]}"}

async def forward_message_single_session(client: TelegramClient, from_peer, msg_id: int, to_peer) -> dict:
    """Forward a message/post to a target destination."""
    if not client.is_connected():
        try:
            await client.connect()
        except Exception as e:
            return {"status": "ERROR", "icon": "🔴", "note": f"Connect Failed: {e}"}

    try:
        from_entity = await client.get_entity(from_peer)
        to_entity = await client.get_entity(to_peer)
        await client.forward_messages(to_entity, msg_id, from_entity)
        target_title = getattr(to_entity, "title", getattr(to_entity, "first_name", str(to_peer)))
        return {"status": "SUCCESS", "icon": "🟢", "note": f"Forwarded to [{target_title}] ✅"}
    except FloodWaitError as fe:
        return {"status": "FLOOD_WAIT", "icon": "⏳", "note": f"FloodWait ({fe.seconds}s) ⚠️"}
    except Exception as e:
        return {"status": "ERROR", "icon": "🔴", "note": f"Failed: {str(e)[:30]}"}

async def report_message_single_session(client: TelegramClient, peer, msg_id: int, reason_key: str, comment: str = "Inappropriate content") -> dict:
    """Report a message/post to Telegram moderation."""
    if not client.is_connected():
        try:
            await client.connect()
        except Exception as e:
            return {"status": "ERROR", "icon": "🔴", "note": f"Connect Failed: {e}"}

    reason_map = {
        "spam": types.InputReportReasonSpam(),
        "fake": types.InputReportReasonFake(),
        "violence": types.InputReportReasonViolence(),
        "pornography": types.InputReportReasonPornography(),
        "child_abuse": types.InputReportReasonChildAbuse(),
        "copyright": types.InputReportReasonCopyright(),
        "other": types.InputReportReasonOther()
    }
    reason_obj = reason_map.get(reason_key.lower(), types.InputReportReasonSpam())

    try:
        entity = await client.get_entity(peer)
        await client(functions.messages.ReportRequest(
            peer=entity,
            id=[msg_id],
            reason=reason_obj,
            message=comment
        ))
        return {"status": "SUCCESS", "icon": "🟢", "note": f"Reported ({reason_key.upper()}) ✅"}
    except FloodWaitError as fe:
        return {"status": "FLOOD_WAIT", "icon": "⏳", "note": f"FloodWait ({fe.seconds}s) ⚠️"}
    except Exception as e:
        return {"status": "ERROR", "icon": "🔴", "note": f"Failed: {str(e)[:30]}"}

async def send_comment_single_session(client: TelegramClient, peer, msg_id: int | None, text_content: str) -> dict:
    """Send message or reply/comment to discussion."""
    if not client.is_connected():
        try:
            await client.connect()
        except Exception as e:
            return {"status": "ERROR", "icon": "🔴", "note": f"Connect Failed: {e}"}

    try:
        entity = await client.get_entity(peer)
        if msg_id:
            await client.send_message(entity, text_content, reply_to=msg_id)
        else:
            await client.send_message(entity, text_content)
        return {"status": "SUCCESS", "icon": "🟢", "note": "Comment/Message Sent ✅"}
    except FloodWaitError as fe:
        return {"status": "FLOOD_WAIT", "icon": "⏳", "note": f"FloodWait ({fe.seconds}s) ⚠️"}
    except Exception as e:
        return {"status": "ERROR", "icon": "🔴", "note": f"Failed: {str(e)[:30]}"}

# ----------------- ZIP & Batch Session Import Engine -----------------

def convert_sqlite_session_to_string(session_file_path: str) -> str | None:
    """Converts a Telethon .session SQLite file to StringSession."""
    try:
        db_path = session_file_path
        if not db_path.endswith(".session"):
            db_path = f"{session_file_path}.session"
        
        if not os.path.exists(db_path):
            return None

        # Base path without extension for SQLiteSession
        base_path = db_path[:-8] if db_path.endswith(".session") else db_path
        sess = SQLiteSession(base_path)
        str_val = StringSession.save(sess)
        sess.close()
        return str_val
    except Exception as e:
        logger.debug(f"Direct SQLiteSession conversion note: {e}")
        try:
            # Direct SQLite query fallback
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT dc_id, server_address, port, auth_key FROM sessions")
            row = cur.fetchone()
            conn.close()
            if row and row[3]:
                dc_id, server_address, port, auth_key = row
                s = StringSession()
                s._dc_id = dc_id
                s._server_address = server_address
                s._port = port
                s._auth_key = types.AuthKey(data=auth_key)
                return StringSession.save(s)
        except Exception:
            pass
        return None

async def import_sessions_from_zip_file(owner_id: int, zip_file_path: str) -> dict:
    """
    Extract and import all sessions from a ZIP file.
    Supports:
    - Telethon SQLite .session files
    - Text files containing Pyrogram / Telethon string sessions
    - JSON files with session mappings
    """
    report = {"total_found": 0, "success": 0, "failed": 0, "details": []}
    temp_dir = tempfile.mkdtemp(prefix="tg_zip_import_")

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zf:
            zf.extractall(temp_dir)

        # Scan all files in extracted directory
        candidate_files = []
        for root, _, files in os.walk(temp_dir):
            for file in files:
                candidate_files.append(os.path.join(root, file))

        report["total_found"] = len(candidate_files)

        for fpath in candidate_files:
            fname = os.path.basename(fpath)
            session_str = None

            # Case A: .session SQLite file
            if fname.endswith(".session"):
                session_str = convert_sqlite_session_to_string(fpath)

            # Case B: Text or JSON file containing string session
            elif fname.endswith((".txt", ".json", ".str", ".string")):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as tf:
                        content = tf.read().strip()
                        # Match Telethon / Pyrogram string session format
                        lines = content.splitlines()
                        for l in lines:
                            l = l.strip()
                            if len(l) > 40 and not l.startswith("#"):
                                session_str = l
                                break
                except Exception:
                    pass

            if not session_str:
                report["failed"] += 1
                report["details"].append(f"• 🔴 `{fname}`: Invalid session format")
                continue

            # Verify and save
            ok, details, err = await verify_and_extract_session_details(session_str)
            if ok and details:
                acc_id = details["account_id"]
                phone = details["phone_number"]
                fn = details["first_name"]
                ln = details["last_name"]
                un = details["username"]
                dc = details["dc_id"]

                await database.save_or_update_session(owner_id, acc_id, phone, session_str, fn, ln, un, dc)
                await start_session(owner_id, acc_id, session_str)
                report["success"] += 1
                report["details"].append(f"• 🟢 **{fn}** (`{phone}`) ➔ DC{dc} Connected ✅")
            else:
                report["failed"] += 1
                report["details"].append(f"• 🔴 `{fname}`: {err or 'Auth failed'}")

            await asyncio.sleep(0.3)

    except Exception as e:
        logger.error(f"Error extracting ZIP file: {e}", exc_info=True)
        report["details"].append(f"❌ ZIP Extraction Error: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return report

async def init_all_sessions():
    active_sessions = await database.get_all_active_sessions()
    logger.info(f"🔄 Initializing {len(active_sessions)} active sessions from database...")
    for s in active_sessions:
        owner_id = s["owner_id"]
        account_id = s["account_id"]
        session_str = s.get("session_string")
        if session_str:
            try:
                await start_session(owner_id, account_id, session_str)
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Error starting session {owner_id}_{account_id}: {e}")

async def shutdown_all_sessions():
    logger.info(f"🛑 Gracefully shutting down {len(active_clients)} active Telethon clients...")
    keys = list(active_clients.keys())
    for k in keys:
        client = active_clients.pop(k, None)
        if client:
            try:
                if client.is_connected():
                    await client.disconnect()
            except Exception:
                pass
    logger.info("✅ All sessions safely disconnected.")

def get_client(owner_id: int, account_id: int) -> TelegramClient | None:
    return active_clients.get(get_client_key(owner_id, account_id))

def get_all_clients_for_user(owner_id: int) -> list[tuple[int, TelegramClient]]:
    prefix = f"{owner_id}_"
    result = []
    for k, client in active_clients.items():
        if k.startswith(prefix):
            acc_id = int(k.replace(prefix, ""))
            result.append((acc_id, client))
    return result
