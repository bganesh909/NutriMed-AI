"""
Unit tests for app.core.security -- JWT, password hashing, AES encryption.
"""

import time
from datetime import timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decrypt_data,
    encrypt_data,
    hash_password,
    verify_access_token,
    verify_password,
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_returns_bcrypt_string(self):
        hashed = hash_password("mypassword")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
        assert hashed != "mypassword"

    def test_verify_correct_password(self):
        hashed = hash_password("CorrectHorse123")
        assert verify_password("CorrectHorse123", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("CorrectHorse123")
        assert verify_password("WrongPassword", hashed) is False

    def test_different_calls_produce_different_hashes(self):
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2  # bcrypt salts each hash

    def test_empty_password_still_hashes(self):
        hashed = hash_password("")
        assert hashed is not None
        assert verify_password("", hashed) is True

    def test_unicode_password(self):
        pwd = "p@$$w0rd_\u00e9\u00e0\u00fc"
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------


class TestJWT:
    def test_create_and_verify_access_token(self):
        token = create_access_token(subject="user123", role="user")
        payload = verify_access_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "user"
        assert "exp" in payload
        assert "iat" in payload

    def test_token_contains_custom_extra_claims(self):
        token = create_access_token(
            subject="user456",
            role="admin",
            extra={"type": "refresh", "org": "nutrimed"},
        )
        payload = verify_access_token(token)
        assert payload["sub"] == "user456"
        assert payload["role"] == "admin"
        assert payload["type"] == "refresh"
        assert payload["org"] == "nutrimed"

    def test_token_respects_custom_expiry(self):
        token = create_access_token(
            subject="u1",
            expires_delta=timedelta(seconds=2),
        )
        payload = verify_access_token(token)
        assert payload["sub"] == "u1"
        # Token should still be valid immediately
        assert payload["exp"] > payload["iat"]

    def test_expired_token_raises(self):
        token = create_access_token(
            subject="u1",
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            verify_access_token(token)

    def test_tampered_token_raises(self):
        token = create_access_token(subject="u1")
        tampered = token[:-4] + "XXXX"
        with pytest.raises(jwt.PyJWTError):
            verify_access_token(tampered)

    def test_token_with_wrong_secret_raises(self):
        payload = {"sub": "u1", "role": "user", "exp": time.time() + 3600}
        bad_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        with pytest.raises(jwt.PyJWTError):
            verify_access_token(bad_token)

    def test_default_role_is_user(self):
        token = create_access_token(subject="u1")
        payload = verify_access_token(token)
        assert payload["role"] == "user"

    def test_admin_role(self):
        token = create_access_token(subject="admin1", role="admin")
        payload = verify_access_token(token)
        assert payload["role"] == "admin"


# ---------------------------------------------------------------------------
# AES encryption / decryption
# ---------------------------------------------------------------------------


class TestAESEncryption:
    def test_encrypt_and_decrypt_roundtrip(self):
        original = b"This is a medical report in plain bytes."
        encrypted = encrypt_data(original)
        assert encrypted != original
        decrypted = decrypt_data(encrypted)
        assert decrypted == original

    def test_different_encryptions_differ(self):
        data = b"Same data encrypted twice."
        e1 = encrypt_data(data)
        e2 = encrypt_data(data)
        # Fernet uses a random IV each time
        assert e1 != e2

    def test_decrypt_wrong_data_raises(self):
        with pytest.raises(Exception):
            decrypt_data(b"not-a-valid-fernet-token")

    def test_large_data_roundtrip(self):
        large = b"X" * 1_000_000  # 1 MB
        encrypted = encrypt_data(large)
        assert decrypt_data(encrypted) == large

    def test_empty_data_roundtrip(self):
        encrypted = encrypt_data(b"")
        assert decrypt_data(encrypted) == b""

    def test_binary_data_roundtrip(self):
        binary = bytes(range(256))
        encrypted = encrypt_data(binary)
        assert decrypt_data(encrypted) == binary
