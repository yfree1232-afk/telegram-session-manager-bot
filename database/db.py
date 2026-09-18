import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from helpers.crypto import encrypt_session, decrypt_session
import config

logger = logging.getLogger("Database")

DEFAULT_VC_MESSAGE = """
Hey {name}! 👋

Voice Chat ({channel}) join karne ke liye shukriya!
Agar aapko koi help chahiye ya connect karna chahte hain toh yahan reply kar sakte hain. 😊
""".strip()

class MongoDatabase:
    def __init__(self, uri: str = config.MONGO_URI, db_name: str = config.DATABASE_NAME):
        self.uri = uri
        self.db_name = db_name
        self._client = None
        self._db = None

    def _ensure_connected(self):
        if self._client is None:
            self._client = AsyncIOMotorClient(self.uri, serverSelectionTimeoutMS=5000)
            self._db = self._client[self.db_name]

    @property
    def client(self):
        self._ensure_connected()
        return self._client

    @property
    def db(self):
        self._ensure_connected()
        return self._db

    @property
    def users(self):
        return self.db["users"]

    @property
    def accounts(self):
        return self.db["accounts"]

    @property
    def counters(self):
        return self.db["counters"]

    @property
    def vc_dm_logs(self):
        return self.db["vc_dm_logs"]

    @property
    def activity_logs(self):
        return self.db["activity_logs"]


    async def init_db(self):
        """Initialize MongoDB indexes."""
        try:
            await self.users.create_index("user_id", unique=True)
            await self.accounts.create_index([("user_id", 1), ("id", 1)])
            await self.accounts.create_index([("owner_id", 1), ("account_id", 1)])
            await self.vc_dm_logs.create_index([("owner_id", 1), ("recipient_id", 1)])
            await self.vc_dm_logs.create_index([("sent_at", -1)])
            await self.activity_logs.create_index([("owner_id", 1), ("timestamp", -1)])
            await self.client.admin.command("ping")
            logger.info(f"🍃 MongoDB Atlas connected & initialized: {config.DATABASE_NAME}")
        except Exception as e:
            logger.warning(f"MongoDB init warning: {e}")

    async def _get_next_sequence(self, name: str = "account_id") -> int:
        ret = await self.counters.find_one_and_update(
            {"_id": name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True
        )
        return ret.get("seq", 1)

    # ---------------- USER OPERATIONS ----------------
    async def add_user(self, user_id: int, first_name: str = "", username: str = None):
        """Register or update user in MongoDB with default settings."""
        now = datetime.datetime.utcnow().isoformat()
        await self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "first_name": first_name or "",
                    "username": username or "",
                    "last_active": now
                },
                "$setOnInsert": {
                    "joined_at": now,
                    "vc_message": DEFAULT_VC_MESSAGE,
                    "vc_msg_type": "text",
                    "vc_media_path": None,
                    "vc_auto_send": 1,
                    "vc_delay": 2.5
                }
            },
            upsert=True
        )

    async def register_user(self, user_id: int, first_name: str = "", username: str = None):
        await self.add_user(user_id, first_name, username)

    async def get_user(self, user_id: int) -> dict | None:
        return await self.users.find_one({"user_id": user_id}, {"_id": 0})

    async def get_users_count(self) -> int:
        return await self.users.count_documents({})

    async def get_all_users(self) -> list:
        cursor = self.users.find({}, {"user_id": 1})
        users = []
        async for doc in cursor:
            users.append(doc["user_id"])
        return users

    # ---------------- ACCOUNT OPERATIONS ----------------
    async def save_account(self, user_id: int, session_type: str, account_name: str, phone: str, tg_user_id: int, raw_session: str, is_active: int = 1, status: str = "ACTIVE") -> int:
        """Encrypt and permanently store session account in MongoDB Atlas."""
        acc_id = await self._get_next_sequence("account_id")
        now = datetime.datetime.utcnow().isoformat()
        encrypted = encrypt_session(raw_session)
        await self.accounts.insert_one({
            "id": acc_id,
            "user_id": user_id,
            "owner_id": user_id,
            "account_id": tg_user_id,
            "session_type": session_type,
            "account_name": account_name,
            "phone": phone,
            "phone_number": phone,
            "first_name": account_name,
            "last_name": "",
            "username": "",
            "tg_user_id": tg_user_id,
            "encrypted_session": encrypted,
            "session_string": raw_session,
            "is_active": is_active,
            "status": status,
            "created_at": now,
            "added_at": now,
            "last_checked": now
        })
        return acc_id

    async def save_or_update_account(
        self,
        owner_id: int,
        account_id: int,
        phone_number: str,
        first_name: str,
        last_name: str = "",
        username: str = "",
        session_string: str = "",
        is_active: int = 1,
        status: str = "ACTIVE",
        session_type: str = "telethon",
        extra_data: dict | None = None
    ) -> int:
        await self.add_user(owner_id, first_name, username)
        now = datetime.datetime.utcnow().isoformat()
        encrypted = encrypt_session(session_string)

        existing = await self.accounts.find_one({"$or": [
            {"owner_id": owner_id, "account_id": account_id},
            {"user_id": owner_id, "id": account_id}
        ]})

        if existing:
            db_id = existing.get("id") or existing.get("account_id")
            await self.accounts.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "phone": phone_number,
                        "phone_number": phone_number,
                        "first_name": first_name,
                        "last_name": last_name,
                        "username": username,
                        "account_name": f"{first_name} {last_name}".strip() or phone_number,
                        "session_string": session_string,
                        "encrypted_session": encrypted,
                        "status": status,
                        "last_checked": now,
                        "extra_data": extra_data or {}
                    }
                }
            )
            return db_id
        else:
            db_id = await self._get_next_sequence("account_id")
            await self.accounts.insert_one({
                "id": db_id,
                "user_id": owner_id,
                "owner_id": owner_id,
                "account_id": account_id,
                "tg_user_id": account_id,
                "phone": phone_number,
                "phone_number": phone_number,
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "account_name": f"{first_name} {last_name}".strip() or phone_number,
                "session_type": session_type,
                "encrypted_session": encrypted,
                "session_string": session_string,
                "is_active": is_active,
                "status": status,
                "created_at": now,
                "added_at": now,
                "last_checked": now,
                "extra_data": extra_data or {}
            })
            return db_id

    async def get_user_accounts(self, user_id: int) -> list:
        if user_id in config.ADMIN_IDS:
            cursor = self.accounts.find({}).sort("id", -1)
        else:
            cursor = self.accounts.find({"$or": [{"user_id": user_id}, {"owner_id": user_id}]}).sort("id", -1)
        accs = []
        async for doc in cursor:
            raw_s = doc.get("session_string") or ""
            if not raw_s and doc.get("encrypted_session"):
                raw_s = decrypt_session(doc.get("encrypted_session"))

            accs.append({
                "id": doc.get("id") or doc.get("account_id"),
                "user_id": doc.get("user_id") or doc.get("owner_id"),
                "owner_id": doc.get("owner_id") or doc.get("user_id"),
                "account_id": doc.get("account_id") or doc.get("tg_user_id"),
                "tg_user_id": doc.get("tg_user_id") or doc.get("account_id"),
                "session_type": doc.get("session_type", "telethon"),
                "account_name": doc.get("account_name") or f"{doc.get('first_name', '')} {doc.get('last_name', '')}".strip() or "User",
                "first_name": doc.get("first_name", ""),
                "last_name": doc.get("last_name", ""),
                "username": doc.get("username", ""),
                "phone": doc.get("phone") or doc.get("phone_number", "Unknown"),
                "phone_number": doc.get("phone_number") or doc.get("phone", "Unknown"),
                "is_active": doc.get("is_active", 1),
                "status": doc.get("status", "ACTIVE"),
                "created_at": doc.get("created_at") or doc.get("added_at", ""),
                "added_at": doc.get("added_at") or doc.get("created_at", ""),
                "last_checked": doc.get("last_checked", ""),
                "raw_session": raw_s,
                "session_string": raw_s,
                "extra_data": doc.get("extra_data", {})
            })
        return accs

    async def get_account(self, account_id: int, user_id: int) -> dict | None:
        query = {"$or": [{"id": account_id}, {"account_id": account_id}]}
        if user_id not in config.ADMIN_IDS:
            user_clause = {"$or": [{"user_id": user_id}, {"owner_id": user_id}]}
            query = {"$and": [query, user_clause]}
        doc = await self.accounts.find_one(query)
        if not doc:
            return None

        raw_s = doc.get("session_string") or ""
        if not raw_s and doc.get("encrypted_session"):
            raw_s = decrypt_session(doc.get("encrypted_session"))

        return {
            "id": doc.get("id") or doc.get("account_id"),
            "user_id": doc.get("user_id") or doc.get("owner_id"),
            "owner_id": doc.get("owner_id") or doc.get("user_id"),
            "account_id": doc.get("account_id") or doc.get("tg_user_id"),
            "tg_user_id": doc.get("tg_user_id") or doc.get("account_id"),
            "session_type": doc.get("session_type", "telethon"),
            "account_name": doc.get("account_name") or f"{doc.get('first_name', '')} {doc.get('last_name', '')}".strip() or "User",
            "first_name": doc.get("first_name", ""),
            "last_name": doc.get("last_name", ""),
            "username": doc.get("username", ""),
            "phone": doc.get("phone") or doc.get("phone_number", "Unknown"),
            "phone_number": doc.get("phone_number") or doc.get("phone", "Unknown"),
            "is_active": doc.get("is_active", 1),
            "status": doc.get("status", "ACTIVE"),
            "created_at": doc.get("created_at") or doc.get("added_at", ""),
            "added_at": doc.get("added_at") or doc.get("created_at", ""),
            "last_checked": doc.get("last_checked", ""),
            "raw_session": raw_s,
            "session_string": raw_s,
            "extra_data": doc.get("extra_data", {})
        }

    async def get_account_by_db_id(self, db_id: int, owner_id: int) -> dict | None:
        return await self.get_account(db_id, owner_id)

    async def toggle_account_active(self, account_id: int, user_id: int) -> bool | None:
        acc = await self.get_account(account_id, user_id)
        if not acc:
            return None
        new_state = 0 if acc.get("is_active", 1) == 1 else 1
        await self.accounts.update_many(
            {"$or": [{"id": account_id}, {"account_id": account_id}], "$or": [{"user_id": user_id}, {"owner_id": user_id}]},
            {"$set": {"is_active": new_state}}
        )
        return bool(new_state)

    async def toggle_all_accounts(self, user_id: int, target_state: int):
        await self.accounts.update_many(
            {"$or": [{"user_id": user_id}, {"owner_id": user_id}]},
            {"$set": {"is_active": target_state}}
        )

    async def update_account_status(self, account_id: int, status: str):
        now = datetime.datetime.utcnow().isoformat()
        await self.accounts.update_many(
            {"$or": [{"id": account_id}, {"account_id": account_id}]},
            {"$set": {"status": status, "last_checked": now}}
        )

    async def delete_account(self, account_id: int, user_id: int) -> bool:
        res = await self.accounts.delete_many({
            "$or": [{"id": account_id}, {"account_id": account_id}],
            "$or": [{"user_id": user_id}, {"owner_id": user_id}]
        })
        return res.deleted_count > 0

    async def count_user_accounts(self, user_id: int) -> int:
        if user_id in config.ADMIN_IDS:
            return await self.accounts.count_documents({})
        return await self.accounts.count_documents({"$or": [{"user_id": user_id}, {"owner_id": user_id}]})

    # ---------------- VC SETTINGS & LOGS ----------------
    async def update_vc_message(self, user_id: int, message: str, msg_type: str = "text", media_path: str | None = None):
        await self.add_user(user_id)
        await self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "vc_message": message,
                    "vc_msg_type": msg_type,
                    "vc_media_path": media_path
                }
            }
        )

    async def toggle_vc_auto_send(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        new_state = 0 if (user and user.get("vc_auto_send") == 1) else 1
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"vc_auto_send": new_state}},
            upsert=True
        )
        return bool(new_state)

    async def update_vc_delay(self, user_id: int, delay: float):
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"vc_delay": delay}},
            upsert=True
        )

    async def has_sent_vc_dm(self, owner_id: int, recipient_id: int) -> bool:
        doc = await self.vc_dm_logs.find_one({"owner_id": owner_id, "recipient_id": recipient_id})
        return doc is not None

    async def log_vc_dm(self, owner_id: int, account_id: int, recipient_id: int, chat_id: str):
        now = datetime.datetime.utcnow().isoformat()
        await self.vc_dm_logs.insert_one({
            "owner_id": owner_id,
            "account_id": account_id,
            "recipient_id": recipient_id,
            "chat_id": str(chat_id),
            "sent_at": now
        })

    async def count_vc_dms_sent(self, owner_id: int) -> int:
        return await self.vc_dm_logs.count_documents({"owner_id": owner_id})

    # ---------------- ACTIVITY LOGS & UTILS ----------------
    async def log_activity(self, owner_id: int, action: str, details: str = ""):
        now = datetime.datetime.utcnow().isoformat()
        await self.activity_logs.insert_one({
            "owner_id": owner_id,
            "action": action,
            "details": details,
            "timestamp": now
        })

    async def get_recent_activity(self, owner_id: int, limit: int = 15) -> list:
        cursor = self.activity_logs.find({"owner_id": owner_id}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def sync_global_sessions_for_user(self, user_id: int):
        cnt = await self.count_user_accounts(user_id)
        if cnt == 0:
            pipeline = [
                {"$group": {
                    "_id": "$account_id",
                    "doc": {"$first": "$$ROOT"}
                }}
            ]
            distinct_accs = await self.accounts.aggregate(pipeline).to_list(length=50)
            now = datetime.datetime.utcnow().isoformat()
            for item in distinct_accs:
                r = item["doc"]
                new_id = await self._get_next_sequence("account_id")
                await self.accounts.update_one(
                    {"$or": [{"owner_id": user_id, "account_id": r["account_id"]}, {"user_id": user_id, "account_id": r["account_id"]}]},
                    {
                        "$setOnInsert": {
                            "id": new_id,
                            "user_id": user_id,
                            "owner_id": user_id,
                            "account_id": r.get("account_id"),
                            "phone": r.get("phone") or r.get("phone_number", ""),
                            "phone_number": r.get("phone_number") or r.get("phone", ""),
                            "first_name": r.get("first_name", ""),
                            "last_name": r.get("last_name", ""),
                            "username": r.get("username", ""),
                            "account_name": r.get("account_name", ""),
                            "session_string": r.get("session_string", ""),
                            "encrypted_session": r.get("encrypted_session", ""),
                            "session_type": r.get("session_type", "telethon"),
                            "is_active": r.get("is_active", 1),
                            "status": "ACTIVE",
                            "created_at": now,
                            "added_at": now,
                            "last_checked": now
                        }
                    },
                    upsert=True
                )

db = MongoDatabase()

# Expose module-level functions for compatibility
init_db = db.init_db
add_user = db.add_user
register_user = db.register_user
get_user = db.get_user
get_users_count = db.get_users_count
get_all_users = db.get_all_users
save_account = db.save_account
save_or_update_account = db.save_or_update_account
get_user_accounts = db.get_user_accounts
get_account = db.get_account
get_account_by_db_id = db.get_account_by_db_id
toggle_account_active = db.toggle_account_active
toggle_all_accounts = db.toggle_all_accounts
update_account_status = db.update_account_status
delete_account = db.delete_account
count_user_accounts = db.count_user_accounts
update_vc_message = db.update_vc_message
toggle_vc_auto_send = db.toggle_vc_auto_send
update_vc_delay = db.update_vc_delay
has_sent_vc_dm = db.has_sent_vc_dm
log_vc_dm = db.log_vc_dm
count_vc_dms_sent = db.count_vc_dms_sent
log_activity = db.log_activity
get_recent_activity = db.get_recent_activity
sync_global_sessions_for_user = db.sync_global_sessions_for_user

