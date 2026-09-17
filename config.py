import os
import asyncio

# Fix for Python 3.12+ / 3.14 event loop compatibility
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

# Telegram Bot Credentials
BOT_TOKEN = os.getenv("BOT_TOKEN", "8973572372:AAFD7hLJ2cPdlOCmcta08m4WkSsISOac-sc")
API_ID = int(os.getenv("API_ID", "30929822"))
API_HASH = os.getenv("API_HASH", "8586e9580c6480b65d23150cec959506")

# Owner / Admin ID
_owner = os.getenv("OWNER_ID") or os.getenv("ADMIN_IDS", "0")
try:
    OWNER_ID = int(_owner.split()[0].split(",")[0])
except Exception:
    OWNER_ID = 0

# Database
DB_NAME = os.getenv("DATABASE_NAME") or os.getenv("DB_NAME", "session_vault.db")

# Encryption Key for Vault Security
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = os.getenv("SECRET_KEY", "uN_4V6z1Fw_14a_XqR8kL9s2M0yPt6Zb3Cw5Er7Tg1I=")
    try:
        Fernet(ENCRYPTION_KEY.encode())
    except Exception:
        ENCRYPTION_KEY = Fernet.generate_key().decode()

# UI Theme & Assets
BOT_NAME = "Session Manager"
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "https://t.me/")
CHANNEL = os.getenv("CHANNEL", "https://t.me/")
START_IMG = os.getenv("START_IMG", "https://graph.org/file/e20f1883317dd4ff3cbfa.jpg")
