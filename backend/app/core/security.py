from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
import bcrypt as _bcrypt
from cryptography.fernet import Fernet
import base64
import hashlib

from app.core.config import settings


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    return _bcrypt.hashpw(plain_password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

def create_access_token(
    subject: str,
    role: str = "user",
    extra: Optional[dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_EXPIRY_MINUTES))
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": expire,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )


# ---------------------------------------------------------------------------
# AES encryption / decryption for medical reports
# ---------------------------------------------------------------------------

def _derive_fernet_key(raw_key: str) -> bytes:
    """Derive a valid 32-byte url-safe base64 Fernet key from an arbitrary string."""
    digest = hashlib.sha256(raw_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    key = _derive_fernet_key(settings.AES_KEY)
    return Fernet(key)


def encrypt_data(data: bytes) -> bytes:
    """Encrypt raw bytes (e.g. report file content)."""
    return get_fernet().encrypt(data)


def decrypt_data(token: bytes) -> bytes:
    """Decrypt previously encrypted data."""
    return get_fernet().decrypt(token)
