"""Fernet encryption utilities for wallet private keys."""

from cryptography.fernet import Fernet

from bot.config import WALLET_ENCRYPTION_KEY


def get_fernet() -> Fernet:
    """Return a Fernet cipher using the configured encryption key."""
    key = WALLET_ENCRYPTION_KEY
    if not key:
        raise ValueError("WALLET_ENCRYPTION_KEY is not set")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_private_key(private_key: str) -> str:
    """Encrypt a private key and return the ciphertext as a string."""
    f = get_fernet()
    return f.encrypt(private_key.encode()).decode()


def decrypt_private_key(encrypted_key: str) -> str:
    """Decrypt an encrypted private key."""
    f = get_fernet()
    return f.decrypt(encrypted_key.encode()).decode()


def generate_encryption_key() -> str:
    """Generate a new Fernet key (for initial setup)."""
    return Fernet.generate_key().decode()
