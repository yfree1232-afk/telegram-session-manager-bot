import asyncio
import logging
from telethon import TelegramClient
import session_manager
import database

logger = logging.getLogger("CustomTasks")

"""
========================================================================================
💡 PLUGGABLE CUSTOM TASK MODULE
========================================================================================
Yahan aap apna custom task / automation add kar sakte hain (jaise: Auto-DM, Channel Poster,
Forwarder, Scraper, Reactions, Group Joiner, etc.)
"""

async def bulk_join_channel_task(owner_id: int, channel_link: str) -> dict:
    """Helper to join a public or private channel across all active accounts."""
    account_tuples = session_manager.get_all_clients_for_user(owner_id)
    if not account_tuples:
        return {"total": 0, "success": 0, "failed": 0, "results": []}

    results = []
    success_count = 0
    fail_count = 0

    for acc_id, client in account_tuples:
        res = await session_manager.join_channel_single_session(client, channel_link)
        results.append({"account_id": acc_id, "result": res})
        if res.get("status") in ("SUCCESS", "ALREADY_MEMBER", "REQUEST_SENT"):
            success_count += 1
        else:
            fail_count += 1
        await asyncio.sleep(1.5)

    return {
        "total": len(account_tuples),
        "success": success_count,
        "failed": fail_count,
        "results": results
    }

