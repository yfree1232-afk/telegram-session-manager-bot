import sys
import asyncio

# Fix Windows console UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Python 3.12+ / 3.14 event loop compatibility
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import logging
import config
from pyrogram import Client, idle
from database.db import db

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("SessionManager")

app = Client(
    name="SessionManagerBot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    plugins=dict(root="plugins"),
    in_memory=True
)

async def main():
    logger.info("Initializing Database...")
    await db.init_db()
    logger.info("Database initialized successfully.")

    logger.info("Starting Telegram Bot...")
    await app.start()
    me = await app.get_me()

    banner = f"""
=====================================================
  SESSION MANAGER VOLTX IS NOW ONLINE!
  Bot Username : @{me.username}
  Bot ID       : {me.id}
  Status       : Active & Running
  Heroku Ready : Yes
=====================================================
"""
    try:
        print(banner)
    except Exception:
        logger.info(f"Bot online as @{me.username}")

    logger.info(f"Bot successfully started as @{me.username}")

    await idle()
    logger.info("Stopping bot...")
    await app.stop()
    logger.info("Bot stopped. Bye!")

if __name__ == "__main__":
    asyncio.run(main())
