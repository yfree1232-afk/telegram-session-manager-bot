import os
import asyncio
import logging
from telethon import TelegramClient, functions, types, events
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError,
    UserDeactivatedError,
    AuthKeyUnregisteredError,
    AuthKeyDuplicatedError,
    SessionPasswordNeededError,
    UserIsBlockedError,
    PhoneNumberBannedError,
    UserPrivacyRestrictedError,
    ChatAdminRequiredError,
    InviteHashExpiredError,
    InviteHashInvalidError,
    UserAlreadyParticipantError
)
from config import API_ID, API_HASH
import database

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ClientManager")

# Pool of live Telethon clients: {account_id: TelegramClient}
active_clients: dict[int, TelegramClient] = {}

# In-memory background auto-monitors: {owner_id: asyncio.Task}
vc_auto_monitors: dict[int, asyncio.Task] = {}

# Track registered event listeners: set of account_id
registered_event_clients: set[int] = set()

def create_telethon_client(session_str: str | None = None) -> TelegramClient:
    """Create Telethon client with official Desktop fingerprint."""
    session = StringSession(session_str) if session_str else StringSession()
    return TelegramClient(
        session=session,
        api_id=API_ID,
        api_hash=API_HASH,
        device_model="Telegram Desktop",
        system_version="Windows 11 x64",
        app_version="5.4.1 x64",
        lang_code="en",
        system_lang_code="en-US"
    )

async def setup_client_vc_event_listeners(client: TelegramClient, account_dict: dict):
    """Register raw MTProto event listeners on the client for zero-latency instant VC participant DMs."""
    account_id = account_dict.get("account_id")
    owner_id = account_dict.get("owner_id")

    if account_id in registered_event_clients:
        return
    registered_event_clients.add(account_id)

    @client.on(events.Raw(types.UpdateGroupCallParticipants))
    async def on_vc_participants_update(event: types.UpdateGroupCallParticipants):
        try:
            call = event.call
            user_data = await database.get_user(owner_id)
            if not user_data or user_data.get("vc_auto_send") != 1:
                return

            vc_msg = (user_data.get("vc_message") or database.DEFAULT_VC_MESSAGE).strip()
            vc_type = user_data.get("vc_msg_type", "text")
            vc_media = user_data.get("vc_media_path")
            vc_delay = float(user_data.get("vc_delay", 2.5))

            for p in event.participants:
                if not hasattr(p, "peer") or not isinstance(p.peer, types.PeerUser):
                    continue
                
                # 🚫 STRICT FILTER: Exclude VC Hosts, Admins, Co-hosts, and Speakers on mic
                if getattr(p, "can_modify_call", False): # VC Host / Call Admin
                    continue
                if not getattr(p, "muted", True): # Currently unmuted / speaking
                    continue
                if getattr(p, "can_self_unmute", False): # Has speaker stage permission
                    continue
                if getattr(p, "video", None) is not None or getattr(p, "presentation", None) is not None:
                    continue
                if getattr(p, "left", False):
                    continue

                uid = p.peer.user_id
                
                # Deduplication check
                already_sent = await database.has_sent_vc_dm(owner_id, uid)
                if already_sent:
                    continue

                try:
                    user_entity = await client.get_entity(uid)
                    if getattr(user_entity, "bot", False) or getattr(user_entity, "deleted", False):
                        continue

                    is_sent = await send_single_vc_dm(
                        client=client,
                        recipient=user_entity,
                        template=vc_msg,
                        msg_type=vc_type,
                        media_path=vc_media,
                        chat_title="Voice Chat"
                    )
                    if is_sent:
                        await database.log_vc_dm(owner_id, account_id, uid, str(getattr(call, "id", "vc")))
                        logger.info(f"⚡ [INSTANT VC EVENT] [{account_dict.get('phone_number')}] Sent live DM to {user_entity.first_name} ({uid})!")
                    
                    await asyncio.sleep(vc_delay)
                except Exception as err:
                    logger.debug(f"Event send error for user {uid}: {err}")
        except Exception as e:
            logger.debug(f"Error handling UpdateGroupCallParticipants: {e}")

async def get_or_create_client(account_dict: dict) -> TelegramClient | None:
    """Get active connected client from pool or initialize and connect a new one."""
    account_id = account_dict.get("account_id")
    session_str = account_dict.get("session_string")
    db_id = account_dict.get("id")
    
    if not account_id or not session_str:
        return None

    client = active_clients.get(account_id)
    if client:
        if not client.is_connected():
            try:
                await client.connect()
            except Exception as e:
                logger.error(f"Error reconnecting client for account {account_id}: {e}")
                return None
        return client

    try:
        client = create_telethon_client(session_str)
        await client.connect()
        if not await client.is_user_authorized():
            if db_id:
                await database.update_account_status(db_id, "EXPIRED")
            return None
        
        await setup_client_vc_event_listeners(client, account_dict)
        active_clients[account_id] = client
        return client
    except Exception as e:
        logger.error(f"Failed to create client for Account ID {account_id}: {e}")
        return None

async def disconnect_client(acc_key: int):
    """Disconnect and remove client from active pool."""
    registered_event_clients.discard(acc_key)
    client = active_clients.pop(acc_key, None)
    if client:
        try:
            if client.is_connected():
                await client.disconnect()
        except Exception:
            pass

async def disconnect_all_clients():
    """Gracefully disconnect all running clients and cancel background monitors."""
    logger.info("🛑 Disconnecting all Telethon clients and monitors...")
    for owner_id, task in list(vc_auto_monitors.items()):
        task.cancel()
    vc_auto_monitors.clear()
    registered_event_clients.clear()

    for db_id, client in list(active_clients.items()):
        try:
            if client.is_connected():
                await client.disconnect()
        except Exception:
            pass
    active_clients.clear()

async def test_session_string(session_str: str) -> tuple[bool, dict | None, str]:
    """Test a Telethon session string and return user info."""
    client = create_telethon_client(session_str)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, None, "Session is expired or unauthorized."
        
        me = await client.get_me()
        user_info = {
            "account_id": me.id,
            "first_name": me.first_name or "",
            "last_name": me.last_name or "",
            "username": me.username or "",
            "phone_number": me.phone or "",
            "is_premium": getattr(me, "premium", False),
            "dc_id": getattr(client.session, "dc_id", None)
        }
        await client.disconnect()
        return True, user_info, "Session is valid."
    except PhoneNumberBannedError:
        return False, None, "Account is banned from Telegram."
    except (AuthKeyUnregisteredError, AuthKeyDuplicatedError, UserDeactivatedError):
        return False, None, "Session revoked or account deactivated."
    except FloodWaitError as fe:
        return False, None, f"FloodWait limit: {fe.seconds} seconds."
    except Exception as e:
        return False, None, f"Connection error: {e}"
    finally:
        if client.is_connected():
            await client.disconnect()

async def test_account_health(account_dict: dict) -> dict:
    """Check health of an existing account and update its DB status."""
    db_id = account_dict.get("id")
    session_str = account_dict.get("session_string")

    if not session_str:
        await database.update_account_status(db_id, "NO_SESSION")
        return {"status": "DEAD", "reason": "No session string found"}

    is_valid, user_info, message = await test_session_string(session_str)

    if is_valid and user_info:
        await database.update_account_info(
            db_id=db_id,
            first_name=user_info["first_name"],
            last_name=user_info["last_name"],
            username=user_info["username"],
            phone_number=user_info["phone_number"]
        )
        await database.update_account_status(db_id, "ACTIVE")
        return {
            "status": "ACTIVE",
            "first_name": user_info["first_name"],
            "username": user_info["username"],
            "phone_number": user_info["phone_number"],
            "account_id": user_info["account_id"],
            "is_premium": user_info["is_premium"],
            "dc_id": user_info["dc_id"],
            "message": "Account is 100% active and healthy!"
        }
    else:
        err_lower = message.lower()
        if "banned" in err_lower:
            db_status = "BANNED"
        elif "expired" in err_lower or "unregistered" in err_lower or "revoked" in err_lower:
            db_status = "EXPIRED"
        elif "floodwait" in err_lower:
            db_status = "FLOOD_WAIT"
        else:
            db_status = "ERROR"

        await database.update_account_status(db_id, db_status)
        await disconnect_client(db_id)
        return {
            "status": db_status,
            "message": message
        }

async def health_check_all_user_accounts(owner_id: int) -> dict:
    """Run concurrent health check on all accounts of a user."""
    accounts = await database.get_user_accounts(owner_id)
    if not accounts:
        return {"total": 0, "active": 0, "dead": 0, "results": []}

    tasks = [test_account_health(acc) for acc in accounts]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    summary = {"total": len(accounts), "active": 0, "dead": 0, "results": []}

    for acc, res in zip(accounts, results):
        if isinstance(res, Exception):
            res_dict = {"status": "ERROR", "message": str(res)}
        else:
            res_dict = res

        if res_dict.get("status") == "ACTIVE":
            summary["active"] += 1
        else:
            summary["dead"] += 1

        summary["results"].append({
            "id": acc["id"],
            "phone": acc["phone_number"],
            "name": acc["first_name"],
            "account_id": acc["account_id"],
            "health": res_dict
        })

    return summary

# =========================================================================
# 🔍 AUTOMATIC GROUP / CHANNEL & LIVE VC FETCHER
# =========================================================================

async def fetch_user_active_vcs(owner_id: int) -> list[dict]:
    """
    Scan top groups/channels of user's connected accounts safely with flood protection
    and return all active Voice Chats (VCs) running right now!
    """
    accounts = await database.get_user_accounts(owner_id)
    active_accs = [acc for acc in accounts if acc.get("is_active") == 1 and acc.get("status") == "ACTIVE"]

    if not active_accs:
        return []

    active_vcs = []
    seen_chat_ids = set()

    for acc in active_accs:
        client = await get_or_create_client(acc)
        if not client or not client.is_connected():
            continue

        try:
            dialogs = await client.get_dialogs(limit=15)
            for d in dialogs:
                if not (d.is_group or d.is_channel):
                    continue

                chat_id_clean = str(d.id).replace("-100", "").replace("-", "")
                if chat_id_clean in seen_chat_ids:
                    continue

                try:
                    if isinstance(d.entity, (types.Channel, types.Chat)):
                        full_chat = await client(functions.channels.GetFullChannelRequest(channel=d.entity))
                    else:
                        full_chat = await client(functions.messages.GetFullChatRequest(chat_id=d.entity.id))

                    call = getattr(full_chat.full_chat, "call", None)
                    if call and not isinstance(call, types.GroupCallDiscarded):
                        seen_chat_ids.add(chat_id_clean)
                        part_count = getattr(full_chat.full_chat, "call_participants_count", 0) or 0
                        username_str = getattr(d.entity, "username", "") or ""
                        active_vcs.append({
                            "id": d.id,
                            "raw_id": chat_id_clean,
                            "title": d.title or "Group Voice Chat",
                            "username": username_str,
                            "participants_count": part_count,
                            "found_via": acc["phone_number"]
                        })
                    await asyncio.sleep(1.0)
                except FloodWaitError as fwe:
                    logger.warning(f"FloodWait on dialog scan: {fwe.seconds}s")
                    break
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Error fetching dialogs for {acc.get('phone_number')}: {e}")

    return active_vcs

# =========================================================================
# 🎙️ MULTI-SESSION VC JOIN & DISTRIBUTED DM ENGINE
# =========================================================================

def format_custom_vc_message(template: str, user_entity, chat_title: str) -> str:
    """Format custom VC message template with dynamic tags and smart username prefix handling."""
    first_name = getattr(user_entity, "first_name", None) or "Friend"
    last_name = getattr(user_entity, "last_name", None) or ""
    full_name = f"{first_name} {last_name}".strip()
    raw_username = getattr(user_entity, "username", None) or ""
    username_tag = f"@{raw_username}" if raw_username else first_name
    
    formatted = template.replace("{name}", first_name)
    formatted = formatted.replace("{first_name}", first_name)
    formatted = formatted.replace("{last_name}", last_name)
    formatted = formatted.replace("{full_name}", full_name)
    formatted = formatted.replace("@{username}", username_tag)
    formatted = formatted.replace("{username}", username_tag)
    formatted = formatted.replace("@@", "@")
    formatted = formatted.replace("{channel}", chat_title or "our Voice Chat")
    return formatted

async def join_group_and_vc(client: TelegramClient, chat_input: str, chat_entity=None, call=None) -> tuple[bool, str]:
    """Ensure client has joined the group/channel AND joined the Voice Chat (VC)."""
    try:
        if chat_entity is None:
            if "/joinchat/" in str(chat_input) or "+" in str(chat_input):
                invite_hash = str(chat_input).split("+")[-1].split("/")[-1].replace("+", "")
                try:
                    chat_entity = await client(functions.messages.ImportChatInviteRequest(invite_hash))
                except UserAlreadyParticipantError:
                    pass
            else:
                try:
                    chat_entity = await client.get_entity(chat_input)
                    if isinstance(chat_entity, (types.Channel, types.Chat)):
                        try:
                            await client(functions.channels.JoinChannelRequest(channel=chat_entity))
                        except Exception:
                            pass
                except Exception as e:
                    return False, f"Cannot access chat: {e}"

        if call:
            try:
                await client(functions.phone.JoinGroupCallRequest(
                    call=call,
                    join_as=types.InputPeerSelf(),
                    params=types.DataJSON(data="{}"),
                    muted=True
                ))
                logger.info(f"🎙️ Client successfully joined VC!")
            except Exception as e:
                logger.warning(f"Note on joining VC group call: {e}")

        return True, "Joined"
    except Exception as e:
        logger.error(f"Error in join_group_and_vc: {e}")
        return False, str(e)

async def send_single_vc_dm(
    client: TelegramClient,
    recipient: types.User,
    template: str,
    msg_type: str,
    media_path: str | None,
    chat_title: str
) -> bool:
    """Send formatted DM (Text/Media/Voice/Sticker) to a single VC participant."""
    formatted_text = format_custom_vc_message(template, recipient, chat_title) if template else None

    try:
        if msg_type == "sticker" and media_path and os.path.exists(media_path):
            await client.send_file(recipient.id, media_path)
        elif msg_type == "voice" and media_path and os.path.exists(media_path):
            await client.send_file(recipient.id, media_path, voice_note=True, caption=formatted_text, parse_mode="html")
        elif msg_type == "video_note" and media_path and os.path.exists(media_path):
            await client.send_file(recipient.id, media_path, video_note=True)
        elif media_path and os.path.exists(media_path):
            await client.send_file(recipient.id, media_path, caption=formatted_text, parse_mode="html")
        elif formatted_text:
            await client.send_message(recipient.id, formatted_text, parse_mode="html")
        return True
    except FloodWaitError as fe:
        logger.warning(f"⏳ Rate-limited while sending VC DM. Sleeping {fe.seconds}s...")
        await asyncio.sleep(fe.seconds + 1)
        return False
    except (UserPrivacyRestrictedError, UserIsBlockedError):
        logger.info(f"🚫 Cannot DM user {recipient.id} (Privacy settings / Blocked).")
        return False
    except Exception as e:
        logger.error(f"❌ Error sending VC DM to {recipient.id}: {e}")
        return False

async def worker_dispatch_session_dms(
    client: TelegramClient,
    account_dict: dict,
    owner_id: int,
    assigned_users: list[types.User],
    template: str,
    msg_type: str,
    media_path: str | None,
    chat_title: str,
    chat_id_str: str,
    delay: float
) -> dict:
    """Worker task that dispatches DMs for a single session across its unique slice of users."""
    session_phone = account_dict.get("phone_number", "Unknown")
    is_premium = account_dict.get("is_premium", False)
    acc_id = account_dict.get("account_id", 0)

    sent = 0
    failed_privacy = 0

    for user in assigned_users:
        is_sent = await send_single_vc_dm(
            client=client,
            recipient=user,
            template=template,
            msg_type=msg_type,
            media_path=media_path,
            chat_title=chat_title
        )

        if is_sent:
            sent += 1
            await database.log_vc_dm(owner_id, acc_id, user.id, chat_id_str)
            logger.info(f"✅ [Multi-VC DM] [{session_phone}] Sent to {user.first_name} ({user.id})")
        else:
            failed_privacy += 1

        await asyncio.sleep(delay)

    return {
        "phone": session_phone,
        "is_premium": is_premium,
        "assigned": len(assigned_users),
        "sent": sent,
        "failed_privacy": failed_privacy
    }

# Real-Time Continuous VC Blaster Tasks: {owner_id: asyncio.Task}
active_vc_blasts: dict[int, asyncio.Task] = {}
active_vc_blast_states: dict[int, dict] = {}

async def fetch_chat_administrators(client: TelegramClient, chat_entity) -> set[int]:
    """Fetch all channel / group administrators and creator IDs to prevent messaging hosts."""
    admin_ids = set()
    try:
        if isinstance(chat_entity, (types.Channel, types.Chat)):
            participants = await client(functions.channels.GetParticipantsRequest(
                channel=chat_entity,
                filter=types.ChannelParticipantsAdmins(),
                offset=0,
                limit=200,
                hash=0
            ))
            for p in getattr(participants, "participants", []):
                if hasattr(p, "user_id"):
                    admin_ids.add(p.user_id)
                elif hasattr(p, "peer") and isinstance(p.peer, types.PeerUser):
                    admin_ids.add(p.peer.user_id)
            for u in getattr(participants, "users", []):
                admin_ids.add(u.id)
    except Exception as e:
        logger.debug(f"Admin fetch note: {e}")
    return admin_ids

async def fetch_all_vc_participants_paginated(client: TelegramClient, call: types.InputGroupCall) -> tuple[list, dict[int, types.User]]:
    """Fetch ALL VC participants using full pagination offset loop (up to 2500+ participants)."""
    all_participants = []
    all_users_dict = {}
    offset = ""
    seen_offsets = set()

    for _ in range(25):
        try:
            res = await client(functions.phone.GetGroupParticipantsRequest(
                call=call,
                ids=[],
                sources=[],
                offset=offset,
                limit=100
            ))
        except Exception as e:
            logger.debug(f"Pagination error for offset '{offset}': {e}")
            break

        current_parts = getattr(res, "participants", []) or []
        all_participants.extend(current_parts)
        
        for u in (getattr(res, "users", []) or []):
            all_users_dict[u.id] = u

        next_offset = getattr(res, "next_offset", "")
        if not next_offset or next_offset in seen_offsets or len(current_parts) == 0:
            break
        seen_offsets.add(offset)
        offset = next_offset
        await asyncio.sleep(0.2)

    return all_participants, all_users_dict

def is_host_or_speaker(p, chat_admin_ids: set[int], all_self_ids: set[int]) -> bool:
    """Strict filter: returns True if participant is Host, Admin, Co-host, or speaking on stage."""
    uid = None
    if hasattr(p, "peer") and isinstance(p.peer, types.PeerUser):
        uid = p.peer.user_id
    elif hasattr(p, "user_id"):
        uid = p.user_id

    if not uid:
        return True
    if uid in chat_admin_ids:
        return True
    if uid in all_self_ids:
        return True
    if getattr(p, "can_modify_call", False): # VC Host / Call Admin
        return True
    if not getattr(p, "muted", True): # Currently unmuted / speaking on mic
        return True
    if getattr(p, "can_self_unmute", False): # Speaker permission on stage
        return True
    if getattr(p, "video", None) is not None or getattr(p, "presentation", None) is not None:
        return True
    if getattr(p, "left", False):
        return True
    return False

async def blast_vc_multi_session(
    owner_id: int,
    chat_input: str,
    status_updater_coro=None
) -> dict:
    """Multi-Session VC Auto-Joiner with Full Pagination and Strict Host/Speaker Filtering."""
    accounts = await database.get_user_accounts(owner_id)
    active_accs = [acc for acc in accounts if acc.get("is_active") == 1 and acc.get("status") == "ACTIVE"]

    if not active_accs:
        return {"success": False, "error": "Koi Active account nahi mila! Pehle account add ya activate karein."}

    if status_updater_coro:
        await status_updater_coro(f"⏳ **[1/4] Connecting `{len(active_accs)}` Sessions & Joining Voice Chat...**")

    # Get primary client
    primary_client = await get_or_create_client(active_accs[0])
    if not primary_client:
        return {"success": False, "error": f"Primary account `{active_accs[0]['phone_number']}` connect nahi ho saka."}

    clean_input = str(chat_input).strip()
    if clean_input.startswith("https://t.me/"):
        clean_input = clean_input.replace("https://t.me/", "")
    elif clean_input.startswith("t.me/"):
        clean_input = clean_input.replace("t.me/", "")

    try:
        if clean_input.isdigit() or (clean_input.startswith("-") and clean_input[1:].isdigit()):
            chat_entity = await primary_client.get_entity(int(clean_input))
        else:
            chat_entity = await primary_client.get_entity(clean_input)
    except Exception as e:
        return {"success": False, "error": f"Chat/Group find nahi ho saka: `{e}`"}

    chat_title = getattr(chat_entity, "title", str(chat_input))

    # Fetch Voice Chat Call
    try:
        if isinstance(chat_entity, (types.Channel, types.Chat)):
            full_chat = await primary_client(functions.channels.GetFullChannelRequest(channel=chat_entity))
        else:
            full_chat = await primary_client(functions.messages.GetFullChatRequest(chat_id=chat_entity.id))
        
        call = getattr(full_chat.full_chat, "call", None)
        if not call or isinstance(call, types.GroupCallDiscarded):
            return {"success": False, "error": f"**{chat_title}** me koi Voice Chat (VC) abhi active nahi hai!"}

        if hasattr(call, "id") and hasattr(call, "access_hash") and not isinstance(call, types.InputGroupCall):
            call = types.InputGroupCall(id=call.id, access_hash=call.access_hash)
    except Exception as e:
        return {"success": False, "error": f"Voice chat fetch error: `{e}`"}

    # Join group & VC across all active sessions
    join_tasks = []
    connected_workers = []

    for acc in active_accs:
        client = await get_or_create_client(acc)
        if client:
            connected_workers.append((client, acc))
            join_tasks.append(join_group_and_vc(client, chat_input, chat_entity, call))

    if not connected_workers:
        return {"success": False, "error": "Koi bhi session Telegram se connect nahi ho saka."}

    await asyncio.gather(*join_tasks, return_exceptions=True)

    if status_updater_coro:
        await status_updater_coro(f"⏳ **[2/4] `{len(connected_workers)}` Sessions Joined VC! Fetching ALL participants with pagination...**")

    # Fetch chat admins to strictly exclude hosts
    chat_admin_ids = await fetch_chat_administrators(primary_client, chat_entity)

    # Fetch all self/worker IDs
    all_self_ids = set()
    for cl, acc in connected_workers:
        try:
            m = await cl.get_me()
            all_self_ids.add(m.id)
            acc["is_premium"] = getattr(m, "premium", False)
        except Exception:
            all_self_ids.add(acc.get("account_id"))

    # Fetch all participants with pagination
    raw_participants, users_dict = await fetch_all_vc_participants_paginated(primary_client, call)
    total_raw_participants = len(raw_participants)

    if total_raw_participants == 0:
        return {"success": False, "error": "Is Voice Chat me koi participant nahi mila!"}

    # Resolve any missing user entities
    missing_uids = []
    for p in raw_participants:
        if hasattr(p, "peer") and isinstance(p.peer, types.PeerUser):
            uid = p.peer.user_id
            if uid not in users_dict:
                missing_uids.append(uid)

    if missing_uids:
        try:
            resolved_users = await primary_client.get_entity(missing_uids)
            if isinstance(resolved_users, list):
                for u in resolved_users:
                    users_dict[u.id] = u
            else:
                users_dict[resolved_users.id] = resolved_users
        except Exception as pe:
            logger.debug(f"Entity resolve note: {pe}")

    # Strict Filtering: Exclude Hosts, Admins, Speakers, Bots, Self, Duplicates
    eligible_users: list[types.User] = []
    skipped_duplicates = 0
    skipped_hosts_or_speakers = 0
    skipped_bots_or_self = 0

    for p in raw_participants:
        if is_host_or_speaker(p, chat_admin_ids, all_self_ids):
            skipped_hosts_or_speakers += 1
            continue

        uid = p.peer.user_id if hasattr(p, "peer") and isinstance(p.peer, types.PeerUser) else getattr(p, "user_id", None)
        if not uid or uid not in users_dict:
            continue

        user_obj = users_dict[uid]
        if getattr(user_obj, "bot", False) or getattr(user_obj, "deleted", False) or user_obj.id in all_self_ids:
            skipped_bots_or_self += 1
            continue

        already_sent = await database.has_sent_vc_dm(owner_id, user_obj.id)
        if already_sent:
            skipped_duplicates += 1
            continue

        eligible_users.append(user_obj)

    if not eligible_users:
        return {
            "success": True,
            "chat_title": chat_title,
            "total_in_vc": total_raw_participants,
            "eligible_count": 0,
            "total_sent": 0,
            "skipped_duplicates": skipped_duplicates,
            "skipped_hosts_or_speakers": skipped_hosts_or_speakers,
            "skipped_bots_or_self": skipped_bots_or_self,
            "sessions_used": len(connected_workers),
            "session_reports": [],
            "message": "Sabhi regular listeners ko pehle hi DM send ho chuka hai (Host/Speaker excluded)!"
        }

    # Partition with Premium Priority
    premium_workers = [w for w in connected_workers if w[1].get("is_premium")]
    standard_workers = [w for w in connected_workers if not w[1].get("is_premium")]
    ordered_workers = premium_workers + standard_workers
    num_workers = len(ordered_workers)

    total_weights = sum(2 if w[1].get("is_premium") else 1 for w in ordered_workers)
    total_users_count = len(eligible_users)

    worker_assignments: list[tuple[TelegramClient, dict, list[types.User]]] = []
    current_idx = 0

    for idx, (cl, acc) in enumerate(ordered_workers):
        weight = 2 if acc.get("is_premium") else 1
        if idx == num_workers - 1:
            assigned_slice = eligible_users[current_idx:]
        else:
            slice_size = max(1, int((weight / total_weights) * total_users_count))
            assigned_slice = eligible_users[current_idx : current_idx + slice_size]
            current_idx += slice_size

        if assigned_slice:
            worker_assignments.append((cl, acc, assigned_slice))

    user_data = await database.get_user(owner_id)
    vc_msg = (user_data.get("vc_message") or database.DEFAULT_VC_MESSAGE).strip()
    vc_type = user_data.get("vc_msg_type", "text")
    vc_media = user_data.get("vc_media_path")
    vc_delay = float(user_data.get("vc_delay", 2.5))
    chat_id_str = str(chat_entity.id)

    if status_updater_coro:
        await status_updater_coro(
            f"🚀 **[3/4] Dispatching DMs to `{len(eligible_users)}` Unique Listeners across `{len(worker_assignments)}` Sessions...**\n"
            f"🛡️ *Strictly Excluded `{skipped_hosts_or_speakers}` Hosts/Speakers/Admins!*"
        )

    dispatch_tasks = [
        worker_dispatch_session_dms(
            client=cl,
            account_dict=acc,
            owner_id=owner_id,
            assigned_users=slice_users,
            template=vc_msg,
            msg_type=vc_type,
            media_path=vc_media,
            chat_title=chat_title,
            chat_id_str=chat_id_str,
            delay=vc_delay
        )
        for cl, acc, slice_users in worker_assignments
    ]

    worker_results = await asyncio.gather(*dispatch_tasks, return_exceptions=True)

    total_sent = 0
    total_failed_privacy = 0
    reports = []

    for res in worker_results:
        if isinstance(res, Exception):
            continue
        total_sent += res.get("sent", 0)
        total_failed_privacy += res.get("failed_privacy", 0)
        reports.append(res)

    return {
        "success": True,
        "chat_title": chat_title,
        "total_in_vc": total_raw_participants,
        "eligible_count": len(eligible_users),
        "total_sent": total_sent,
        "skipped_duplicates": skipped_duplicates,
        "skipped_hosts_or_speakers": skipped_hosts_or_speakers,
        "skipped_bots_or_self": skipped_bots_or_self,
        "failed_privacy": total_failed_privacy,
        "sessions_used": len(worker_assignments),
        "session_reports": reports
    }

# =========================================================================
# 🔄 24x7 CONTINUOUS VC DISPATCH ENGINE (Runs continuously until VC ends)
# =========================================================================

async def continuous_vc_blaster_loop(owner_id: int, chat_input: str, status_updater_coro=None):
    """
    Background Task: Continuous Voice Chat Blaster.
    Runs continuously as long as Voice Chat is active, sending DMs to every newly joined listener!
    """
    logger.info(f"🚀 [Continuous VC Blaster] Started for User {owner_id} on {chat_input}")
    
    cycle_num = 0
    total_sent_lifetime = 0

    while True:
        try:
            cycle_num += 1
            res = await blast_vc_multi_session(owner_id, chat_input, status_updater_coro=(status_updater_coro if cycle_num == 1 else None))
            
            if not res.get("success"):
                if "abhi active nahi hai" in str(res.get("error", "")):
                    if status_updater_coro:
                        await status_updater_coro(f"⏹️ **Voice Chat Ended!**\nTotal DMs Sent: `{total_sent_lifetime}`")
                    break
            else:
                sent_now = res.get("total_sent", 0)
                total_sent_lifetime += sent_now
                if status_updater_coro and cycle_num > 1 and sent_now > 0:
                    await status_updater_coro(
                        f"🔴 **VC Continuous Live Blaster (ACTIVE)**\n\n"
                        f"• 🎙️ **VC Title:** `{res.get('chat_title')}`\n"
                        f"• 👥 **Listeners in VC:** `{res.get('total_in_vc')}`\n"
                        f"• 🛡️ **Host/Speakers Filtered:** `{res.get('skipped_hosts_or_speakers')}` (0 msgs to host)\n"
                        f"• ⚡ **New DMs in Cycle {cycle_num}:** `+{sent_now}`\n"
                        f"• 📊 **Total Delivered:** `{total_sent_lifetime}`\n\n"
                        f"🔄 *Naye join hone wale members ko real-time DMs ja rahe hain...*"
                    )

        except asyncio.CancelledError:
            logger.info(f"⏹️ [Continuous VC Blaster] Stopped by user {owner_id}")
            break
        except Exception as e:
            logger.debug(f"Continuous blast cycle error: {e}")

        # Wait between polling cycles
        await asyncio.sleep(8)

def start_continuous_vc_blast(owner_id: int, chat_input: str, status_updater_coro=None) -> asyncio.Task:
    """Launch continuous VC blaster in the background."""
    stop_continuous_vc_blast(owner_id)
    task = asyncio.create_task(continuous_vc_blaster_loop(owner_id, chat_input, status_updater_coro))
    active_vc_blasts[owner_id] = task
    return task

def stop_continuous_vc_blast(owner_id: int) -> bool:
    """Stop continuous VC blaster."""
    task = active_vc_blasts.pop(owner_id, None)
    if task and not task.done():
        task.cancel()
        return True
    return False

def is_vc_blast_running(owner_id: int) -> bool:
    """Check if continuous VC blaster is currently running."""
    task = active_vc_blasts.get(owner_id)
    return bool(task and not task.done())

# =========================================================================
# ⚡ FULLY AUTOMATIC BACKGROUND VC AUTO-DM MONITOR
# =========================================================================

async def vc_auto_monitor_loop(owner_id: int):
    """
    Continuous Background Engine:
    Initializes clients and attaches live MTProto event listeners for zero-latency VC DM dispatch.
    Also runs periodic gentle scan every 30s with flood protection.
    """
    logger.info(f"🟢 [VC Auto-Monitor] Event-driven watcher initialized for User {owner_id}")
    
    while True:
        try:
            user_data = await database.get_user(owner_id)
            if not user_data or user_data.get("vc_auto_send") != 1:
                break

            accounts = await database.get_user_accounts(owner_id)
            active_accs = [a for a in accounts if a.get("is_active") == 1 and a.get("status") == "ACTIVE"]

            if not active_accs:
                await asyncio.sleep(25)
                continue

            # Ensure all active accounts have live connected clients with event listeners attached
            for acc in active_accs:
                await get_or_create_client(acc)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Monitor loop heartbeat for user {owner_id}: {e}")

        await asyncio.sleep(30)

def start_vc_auto_monitor(owner_id: int):
    """Start or restart the background automatic VC watcher."""
    stop_vc_auto_monitor(owner_id)
    vc_auto_monitors[owner_id] = asyncio.create_task(vc_auto_monitor_loop(owner_id))

def stop_vc_auto_monitor(owner_id: int):
    """Stop background automatic VC watcher."""
    task = vc_auto_monitors.pop(owner_id, None)
    if task and not task.done():
        task.cancel()
