"""Fernet symmetric encryption for user API keys."""
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from core.config import get_settings

logger = logging.getLogger(__name__)

_cipher: Optional[Fernet] = None


def _get_cipher() -> Fernet:
    global _cipher
    if _cipher is None:
        settings = get_settings()
        if not settings.encryption_key:
            raise RuntimeError(
                "ENCRYPTION_KEY not set. Generate one with: "
                'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        _cipher = Fernet(settings.encryption_key.encode())
    return _cipher


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value and return the ciphertext as a string."""
    return _get_cipher().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a ciphertext string back to plaintext."""
    try:
        return _get_cipher().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt value — invalid token or wrong key")
        raise ValueError("Decryption failed")
