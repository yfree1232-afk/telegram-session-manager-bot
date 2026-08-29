import os
from dotenv import load_dotenv

load_dotenv()

API_ID_RAW = os.getenv("API_ID", "").strip()
API_HASH = os.getenv("API_HASH", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

try:
    API_ID = int(API_ID_RAW) if API_ID_RAW else 2040
except ValueError:
    API_ID = 2040

if not API_HASH:
    API_HASH = "b18441a1ff607e10a989891a5462e627"

ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "8721437284").strip()
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]
if 8721437284 not in ADMIN_IDS:
    ADMIN_IDS.append(8721437284)

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://yfree1232_db_user:NtdjPUmAgl7iEuKE@uploder.6fhrdxh.mongodb.net/?appName=Uploder").strip()
DB_NAME = os.getenv("DATABASE_NAME", "telegram_session_manager").strip()
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions.db")

DB_ENGINE = "mongodb" if MONGO_URI else "sqlite"

