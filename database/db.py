import aiosqlite
import datetime
from helpers.crypto import encrypt_session, decrypt_session
import config

class Database:
    def __init__(self, db_path: str = config.DB_NAME):
        self.db_path = db_path

    async def init_db(self):
        """Initialize SQLite tables for users and session accounts."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    created_at TEXT
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_type TEXT,
                    account_name TEXT,
                    phone TEXT,
                    tg_user_id INTEGER,
                    encrypted_session TEXT,
                    created_at TEXT
                )
            """)
            await conn.commit()

    async def add_user(self, user_id: int, first_name: str, username: str = None):
        """Register user on /start."""
        now = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, first_name, username, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name=excluded.first_name,
                    username=excluded.username
                """,
                (user_id, first_name, username, now)
            )
            await conn.commit()

    async def get_users_count(self) -> int:
        """Count total bot users."""
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("SELECT COUNT(*) FROM users") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_all_users(self) -> list:
        """Get all user IDs for broadcasting."""
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("SELECT user_id FROM users") as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows]

    async def save_account(self, user_id: int, session_type: str, account_name: str, phone: str, tg_user_id: int, raw_session: str) -> int:
        """Save encrypted session into user vault."""
        now = datetime.datetime.utcnow().isoformat()
        encrypted = encrypt_session(raw_session)
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO accounts (user_id, session_type, account_name, phone, tg_user_id, encrypted_session, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, session_type, account_name, phone, tg_user_id, encrypted, now)
            )
            await conn.commit()
            return cursor.lastrowid

    async def get_user_accounts(self, user_id: int) -> list:
        """Fetch all accounts saved by a user."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT id, session_type, account_name, phone, tg_user_id, created_at FROM accounts WHERE user_id = ? ORDER BY id DESC",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_account(self, account_id: int, user_id: int) -> dict:
        """Fetch single account with decrypted session string."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM accounts WHERE id = ? AND user_id = ?",
                (account_id, user_id)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                data = dict(row)
                data["raw_session"] = decrypt_session(data["encrypted_session"])
                return data

    async def delete_account(self, account_id: int, user_id: int) -> bool:
        """Remove an account from user vault."""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "DELETE FROM accounts WHERE id = ? AND user_id = ?",
                (account_id, user_id)
            )
            await conn.commit()
            return cursor.rowcount > 0

db = Database()
