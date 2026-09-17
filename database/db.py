import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from helpers.crypto import encrypt_session, decrypt_session
import config

class MongoDatabase:
    def __init__(self, uri: str = config.MONGO_URI, db_name: str = config.DATABASE_NAME):
        self.client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.users = self.db["users"]
        self.accounts = self.db["accounts"]
        self.counters = self.db["counters"]

    async def init_db(self):
        """Initialize MongoDB indexes."""
        await self.users.create_index("user_id", unique=True)
        await self.accounts.create_index([("user_id", 1), ("id", 1)])
        # Ping server to verify connectivity
        await self.client.admin.command("ping")

    async def _get_next_sequence(self, name: str) -> int:
        ret = await self.counters.find_one_and_update(
            {"_id": name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True
        )
        return ret["seq"]

    async def add_user(self, user_id: int, first_name: str, username: str = None):
        """Register or update user in MongoDB."""
        now = datetime.datetime.utcnow().isoformat()
        await self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "first_name": first_name,
                    "username": username,
                    "last_active": now
                },
                "$setOnInsert": {
                    "joined_at": now
                }
            },
            upsert=True
        )

    async def get_users_count(self) -> int:
        return await self.users.count_documents({})

    async def get_all_users(self) -> list:
        cursor = self.users.find({}, {"user_id": 1})
        users = []
        async for doc in cursor:
            users.append(doc["user_id"])
        return users

    async def save_account(self, user_id: int, session_type: str, account_name: str, phone: str, tg_user_id: int, raw_session: str) -> int:
        """Encrypt and permanently store session account in MongoDB Atlas."""
        acc_id = await self._get_next_sequence("account_id")
        now = datetime.datetime.utcnow().isoformat()
        encrypted = encrypt_session(raw_session)
        await self.accounts.insert_one({
            "id": acc_id,
            "user_id": user_id,
            "session_type": session_type,
            "account_name": account_name,
            "phone": phone,
            "tg_user_id": tg_user_id,
            "encrypted_session": encrypted,
            "created_at": now
        })
        return acc_id

    async def get_user_accounts(self, user_id: int) -> list:
        cursor = self.accounts.find({"user_id": user_id}).sort("id", -1)
        accs = []
        async for doc in cursor:
            accs.append({
                "id": doc["id"],
                "user_id": doc["user_id"],
                "session_type": doc["session_type"],
                "account_name": doc["account_name"],
                "phone": doc.get("phone"),
                "tg_user_id": doc.get("tg_user_id"),
                "created_at": doc.get("created_at", "")
            })
        return accs

    async def get_account(self, account_id: int, user_id: int) -> dict:
        doc = await self.accounts.find_one({"id": account_id, "user_id": user_id})
        if not doc:
            return None
        return {
            "id": doc["id"],
            "user_id": doc["user_id"],
            "session_type": doc["session_type"],
            "account_name": doc["account_name"],
            "phone": doc.get("phone"),
            "tg_user_id": doc.get("tg_user_id"),
            "created_at": doc.get("created_at", ""),
            "raw_session": decrypt_session(doc.get("encrypted_session", ""))
        }

    async def delete_account(self, account_id: int, user_id: int) -> bool:
        res = await self.accounts.delete_one({"id": account_id, "user_id": user_id})
        return res.deleted_count > 0

db = MongoDatabase()
