"""
Encryption utilities for OpenRecords.
Uses Fernet for symmetric encryption of user master keys.
"""
from cryptography.fernet import Fernet

from config import settings


# Initialize Fernet cipher with server secret key
# Ensure the key is properly formatted for Fernet (32 bytes, URL-safe base64)
def _get_fernet_key(secret: str) -> bytes:
    """Generate a valid Fernet key from a secret string."""
    import base64
    import hashlib

    # Hash the secret to get 32 bytes, then encode as base64
    key_bytes = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)


# Create Fernet instance
_fernet = Fernet(_get_fernet_key(settings.openrecords_secret_key))


def encrypt_master_key(user_key: bytes) -> str:
    """
    Encrypt a user's master key using server secret.

    Args:
        user_key: The raw user master key bytes

    Returns:
        Encrypted key as a base64 string
    """
    encrypted = _fernet.encrypt(user_key)
    return encrypted.decode("utf-8")


def decrypt_master_key(encrypted_key: str) -> bytes:
    """
    Decrypt a user's master key.

    Args:
        encrypted_key: The encrypted key as a base64 string

    Returns:
        Decrypted key bytes
    """
    return _fernet.decrypt(encrypted_key.encode("utf-8"))


def generate_user_master_key() -> bytes:
    """Generate a new random master key for a user."""
    return Fernet.generate_key()


def encrypt_bytes_with_user_key(user_key: bytes, data: bytes) -> bytes:
    """Encrypt bytes with a user master key."""
    return Fernet(user_key).encrypt(data)


def decrypt_bytes_with_user_key(user_key: bytes, data: bytes) -> bytes:
    """Decrypt bytes with a user master key."""
    return Fernet(user_key).decrypt(data)


def encrypt_text_with_user_key(user_key: bytes, text: str) -> str:
    """Encrypt text with a user master key."""
    encrypted = encrypt_bytes_with_user_key(user_key, text.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_text_with_user_key(user_key: bytes, encrypted_text: str) -> str:
    """Decrypt text with a user master key."""
    decrypted = decrypt_bytes_with_user_key(user_key, encrypted_text.encode("utf-8"))
    return decrypted.decode("utf-8")
