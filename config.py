import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

# Telegram Bot Credentials
BOT_TOKEN = os.getenv("BOT_TOKEN", "8973572372:AAGBWhOoPbHBCgYwVnT_h4lXyVBAnypBjb4")
# Telegram App Credentials (my.telegram.org verified developer API)
API_ID = int(os.getenv("API_ID", "30929822"))
API_HASH = os.getenv("API_HASH", "8586e9580c6480b65d23150cec959506")

# Owner / Admin ID
_owner = os.getenv("OWNER_ID", "8828864427")
try:
    OWNER_ID = int(_owner.split()[0].split(",")[0])
except Exception:
    OWNER_ID = 8828864427

ADMIN_IDS = [8828864427, 8721437284]
try:
    _raw_admins = os.getenv("ADMIN_IDS", "")
    if _raw_admins:
        for a in _raw_admins.replace(",", " ").split():
            if a.isdigit() and int(a) not in ADMIN_IDS:
                ADMIN_IDS.append(int(a))
except Exception:
    pass

MAX_SESSIONS_PER_USER = int(os.getenv("MAX_SESSIONS_PER_USER", "50"))

# MongoDB Atlas Database
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://yfree1232_db_user:NtdjPUmAgl7iEuKE@uploder.6fhrdxh.mongodb.net/?appName=Uploder"
)
DATABASE_NAME = os.getenv("DATABASE_NAME", "telegram_session_manager")
DB_NAME = DATABASE_NAME

# Encryption Key for Ultra Secure Vault Storage
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = os.getenv("SECRET_KEY", "uN_4V6z1Fw_14a_XqR8kL9s2M0yPt6Zb3Cw5Er7Tg1I=")
    try:
        Fernet(ENCRYPTION_KEY.encode())
    except Exception:
        ENCRYPTION_KEY = Fernet.generate_key().decode()

# UI Theme & Assets
BOT_NAME = "ICE Session Bot"
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "https://t.me/")
CHANNEL = os.getenv("CHANNEL", "https://t.me/")
START_IMG = os.getenv("START_IMG", "https://graph.org/file/e20f1883317dd4ff3cbfa.jpg")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

