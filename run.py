import asyncio
import logging
import signal
import sys
from config import BOT_TOKEN, API_ID, API_HASH, DB_ENGINE
import database
import session_manager
from bot import bot, dp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MainRunner")

async def on_startup():
    logger.info("🚀 Starting Telegram Session Manager Bot...")
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN is missing! Please configure it in .env.")
        sys.exit(1)
    if not API_ID or not API_HASH:
        logger.error("❌ API_ID or API_HASH is missing! Please configure them in .env.")
        sys.exit(1)

    await database.init_db()
    await session_manager.init_all_sessions()
    
    bot_info = await bot.get_me()
    logger.info(f"🤖 Bot Online: @{bot_info.username} (ID: {bot_info.id})")
    logger.info(f"🍃 Database Engine: {DB_ENGINE.upper()}")

async def on_shutdown():
    logger.info("🛑 Shutting down bot gracefully...")
    await session_manager.shutdown_all_sessions()
    await bot.session.close()
    logger.info("✅ Shutdown complete. Bye!")

async def main():
    await on_startup()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await on_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Bot stopped by user.")
