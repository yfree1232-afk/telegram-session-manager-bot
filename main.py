import sys
import asyncio

# Fix for Pyrogram import on Python 3.12+ / 3.14
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import logging

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
from database.db import db
from handlers.start import router as start_router
from handlers.generate import router as generate_router
from handlers.devices import router as devices_router
from handlers.vault import router as vault_router
from handlers.vc import router as vc_router
from handlers.broadcast import router as broadcast_router
from handlers.tools import router as tools_router
from handlers.admin import router as admin_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")
logger = logging.getLogger("SessionManager")

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Register modular routers
dp.include_router(start_router)
dp.include_router(generate_router)
dp.include_router(devices_router)
dp.include_router(vault_router)
dp.include_router(vc_router)
dp.include_router(broadcast_router)
dp.include_router(tools_router)
dp.include_router(admin_router)


async def main():
    logger.info("Initializing Database...")
    await db.init_db()
    logger.info("Database initialized successfully.")

    me = await bot.get_me()
    banner = f"""
=====================================================
  SESSION MANAGER VOLTX IS NOW ONLINE!
  Bot Username : @{me.username}
  Bot ID       : {me.id}
  Framework    : Aiogram 3 (High-Speed Bot API)
  Engines      : Pyrogram v2 + Telethon
  Status       : Active & Responding
=====================================================
"""
    try:
        print(banner)
    except Exception:
        pass

    logger.info(f"Bot successfully started as @{me.username}!")
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        logger.info("Webhook cleared for immediate long polling.")
    except Exception as e:
        logger.warning(f"Note on webhook clear: {e}")

    await dp.start_polling(bot, drop_pending_updates=False)

if __name__ == "__main__":
    asyncio.run(main())
