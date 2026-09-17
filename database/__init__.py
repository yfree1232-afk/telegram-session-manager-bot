# Database package init
from .db import (
    db, init_db, add_user, register_user, get_user, get_users_count, get_all_users,
    save_account, save_or_update_account, get_user_accounts, get_account, get_account_by_db_id,
    toggle_account_active, toggle_all_accounts, update_account_status, delete_account,
    count_user_accounts, update_vc_message, toggle_vc_auto_send, update_vc_delay,
    has_sent_vc_dm, log_vc_dm, count_vc_dms_sent, log_activity, get_recent_activity,
    sync_global_sessions_for_user, DEFAULT_VC_MESSAGE
)

__all__ = [
    "db", "init_db", "add_user", "register_user", "get_user", "get_users_count", "get_all_users",
    "save_account", "save_or_update_account", "get_user_accounts", "get_account", "get_account_by_db_id",
    "toggle_account_active", "toggle_all_accounts", "update_account_status", "delete_account",
    "count_user_accounts", "update_vc_message", "toggle_vc_auto_send", "update_vc_delay",
    "has_sent_vc_dm", "log_vc_dm", "count_vc_dms_sent", "log_activity", "get_recent_activity",
    "sync_global_sessions_for_user", "DEFAULT_VC_MESSAGE"
]

