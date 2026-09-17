import asyncio
from pyrogram import Client
from pyrogram.types import Message

# Active listeners: chat_id -> asyncio.Future
LISTENERS = {}

async def wait_for_input(client: Client, chat_id: int, timeout: int = 120) -> Message:
    """
    Wait for next message from a specific chat_id with timeout.
    Returns Message object or raises asyncio.TimeoutError or ValueError if cancelled.
    """
    loop = asyncio.get_event_loop()
    fut = loop.create_future()
    LISTENERS[chat_id] = fut

    try:
        msg = await asyncio.wait_for(fut, timeout=timeout)
        return msg
    finally:
        LISTENERS.pop(chat_id, None)

def cancel_input(chat_id: int):
    """Cancel any active waiting input for a user."""
    fut = LISTENERS.pop(chat_id, None)
    if fut and not fut.done():
        fut.set_exception(ValueError("Cancelled"))
