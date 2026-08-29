import os
import logging
from datetime import datetime
from config import DB_ENGINE, MONGO_URI, DB_NAME, SQLITE_DB_PATH

logger = logging.getLogger("Database")

_mongo_client = None
_mongo_db = None
_sqlite_path = SQLITE_DB_PATH

async def init_db():
    global _mongo_client, _mongo_db
    if DB_ENGINE == "mongodb" and MONGO_URI:
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            _mongo_client = AsyncIOMotorClient(MONGO_URI)
            _mongo_db = _mongo_client[DB_NAME]
            await _mongo_client.admin.command('ping')
            await _mongo_db["sessions"].create_index([("owner_id", 1), ("account_id", 1)], unique=True)
            await _mongo_db["sessions"].create_index("owner_id")
            await _mongo_db["sessions"].create_index("is_active")
            logger.info("🍃 Connected to MongoDB Atlas successfully!")
            return
        except Exception as e:
            logger.warning(f"⚠️ MongoDB connection failed: {e}. Falling back to SQLite...")

    import aiosqlite
    async with aiosqlite.connect(_sqlite_path) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                phone_number TEXT,
                session_string TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                dc_id INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                status_note TEXT DEFAULT 'Authorized',
                created_at TEXT,
                last_active TEXT,
                UNIQUE(owner_id, account_id)
            )
        ''')
        await db.commit()
    logger.info(f"💾 Initialized SQLite Database at: {_sqlite_path}")

async def save_or_update_session(owner_id: int, account_id: int, phone_number: str, session_string: str, first_name: str = "", last_name: str = "", username: str = "", dc_id: int = 0):
    now_str = datetime.utcnow().isoformat()
    if _mongo_db is not None:
        await _mongo_db["sessions"].update_one(
            {"owner_id": owner_id, "account_id": account_id},
            {
                "$set": {
                    "phone_number": phone_number,
                    "session_string": session_string,
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "dc_id": dc_id,
                    "is_active": 1,
                    "status_note": "Authorized",
                    "last_active": now_str
                },
                "$setOnInsert": {
                    "created_at": now_str
                }
            },
            upsert=True
        )
        return

    import aiosqlite
    async with aiosqlite.connect(_sqlite_path) as db:
        await db.execute('''
            INSERT INTO sessions (owner_id, account_id, phone_number, session_string, first_name, last_name, username, dc_id, is_active, status_note, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'Authorized', ?, ?)
            ON CONFLICT(owner_id, account_id) DO UPDATE SET
                phone_number=excluded.phone_number,
                session_string=excluded.session_string,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                username=excluded.username,
                dc_id=excluded.dc_id,
                is_active=1,
                status_note='Authorized',
                last_active=excluded.last_active
        ''', (owner_id, account_id, phone_number, session_string, first_name, last_name, username, dc_id, now_str, now_str))
        await db.commit()

async def get_user_sessions(owner_id: int) -> list[dict]:
    if _mongo_db is not None:
        cursor = _mongo_db["sessions"].find({"owner_id": owner_id})
        return await cursor.to_list(length=None)

    import aiosqlite
    async with aiosqlite.connect(_sqlite_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sessions WHERE owner_id = ? ORDER BY id ASC", (owner_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_session(owner_id: int, account_id: int) -> dict | None:
    if _mongo_db is not None:
        return await _mongo_db["sessions"].find_one({"owner_id": owner_id, "account_id": account_id})

    import aiosqlite
    async with aiosqlite.connect(_sqlite_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sessions WHERE owner_id = ? AND account_id = ?", (owner_id, account_id)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def delete_session(owner_id: int, account_id: int) -> bool:
    if _mongo_db is not None:
        res = await _mongo_db["sessions"].delete_one({"owner_id": owner_id, "account_id": account_id})
        return res.deleted_count > 0

    import aiosqlite
    async with aiosqlite.connect(_sqlite_path) as db:
        cur = await db.execute("DELETE FROM sessions WHERE owner_id = ? AND account_id = ?", (owner_id, account_id))
        await db.commit()
        return cur.rowcount > 0

async def toggle_session_active(owner_id: int, account_id: int) -> bool:
    sess = await get_session(owner_id, account_id)
    if not sess:
        return False
    current_active = bool(sess.get("is_active", 1))
    new_active = 0 if current_active else 1

    if _mongo_db is not None:
        await _mongo_db["sessions"].update_one(
            {"owner_id": owner_id, "account_id": account_id},
            {"$set": {"is_active": new_active}}
        )
    else:
        import aiosqlite
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute("UPDATE sessions SET is_active = ? WHERE owner_id = ? AND account_id = ?", (new_active, owner_id, account_id))
            await db.commit()

    return bool(new_active)

async def update_session_health(owner_id: int, account_id: int, is_active: bool, status_note: str):
    active_int = 1 if is_active else 0
    now_str = datetime.utcnow().isoformat()
    if _mongo_db is not None:
        await _mongo_db["sessions"].update_one(
            {"owner_id": owner_id, "account_id": account_id},
            {"$set": {"is_active": active_int, "status_note": status_note, "last_active": now_str}}
        )
    else:
        import aiosqlite
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute("UPDATE sessions SET is_active = ?, status_note = ?, last_active = ? WHERE owner_id = ? AND account_id = ?", (active_int, status_note, now_str, owner_id, account_id))
            await db.commit()

async def get_all_active_sessions() -> list[dict]:
    if _mongo_db is not None:
        cursor = _mongo_db["sessions"].find({"is_active": 1})
        return await cursor.to_list(length=None)

    import aiosqlite
    async with aiosqlite.connect(_sqlite_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sessions WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_stats() -> dict:
    if _mongo_db is not None:
        total_sessions = await _mongo_db["sessions"].count_documents({})
        active_sessions = await _mongo_db["sessions"].count_documents({"is_active": 1})
        distinct_users = len(await _mongo_db["sessions"].distinct("owner_id"))
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_users": distinct_users,
            "engine": "MongoDB Atlas"
        }

    import aiosqlite
    async with aiosqlite.connect(_sqlite_path) as db:
        async with db.execute("SELECT COUNT(*), SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END), COUNT(DISTINCT owner_id) FROM sessions") as cursor:
            row = await cursor.fetchone()
            return {
                "total_sessions": row[0] or 0,
                "active_sessions": row[1] or 0,
                "total_users": row[2] or 0,
                "engine": "SQLite"
            }
