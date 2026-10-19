import base64
import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt as _bcrypt
import jwt
from cryptography.fernet import Fernet

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
    extra: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_EXPIRY_MINUTES))
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": expire,
        # Unique per token. Without it, two tokens minted for the same subject
        # within the same second are byte-identical (iat/exp are second-
        # granularity), so a refresh would hand back the caller's current token.
        "jti": uuid.uuid4().hex,
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


def token_predates_password_change(payload: dict[str, Any], user_doc: dict) -> bool:
    """
    True if the token was issued before the user's last password change, so a
    password reset signs out every existing session. Compared at whole-second
    granularity because JWT ``iat`` is an integer timestamp.
    """
    changed_at = user_doc.get("password_changed_at")
    issued_at = payload.get("iat")
    if not changed_at or issued_at is None:
        return False
    if changed_at.tzinfo is None:
        # MongoDB returns naive datetimes that are in UTC.
        changed_at = changed_at.replace(tzinfo=UTC)
    return int(issued_at) < int(changed_at.timestamp())


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
