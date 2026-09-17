from cryptography.fernet import Fernet
import config

try:
    _cipher = Fernet(config.ENCRYPTION_KEY.encode())
except Exception:
    # If invalid key format, generate a new safe one
    key = Fernet.generate_key()
    _cipher = Fernet(key)

def encrypt_session(raw_session: str) -> str:
    """Encrypt session string before storing in database."""
    if not raw_session:
        return ""
    return _cipher.encrypt(raw_session.strip().encode("utf-8")).decode("utf-8")

def decrypt_session(encrypted_session: str) -> str:
    """Decrypt session string when retrieving from database."""
    if not encrypted_session:
        return ""
    try:
        return _cipher.decrypt(encrypted_session.encode("utf-8")).decode("utf-8")
    except Exception:
        # If decryption fails (e.g. key changed), return empty or raw if not encrypted
        return ""
