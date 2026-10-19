"""Startup refuses placeholder or weak secrets unless DEBUG is on."""

import logging
import re
import secrets
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.core.secrets_check import InsecureSecretsError, enforce_secrets, secret_problems

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture()
def security_log(caplog):
    """
    Capture nutrimed.security directly: app.main turns off propagation for the
    "nutrimed" logger, so once any test imports it the root-level caplog
    handler would never see these records.
    """
    logger = logging.getLogger("nutrimed.security")
    logger.addHandler(caplog.handler)
    caplog.set_level(logging.WARNING, logger="nutrimed.security")
    yield caplog
    logger.removeHandler(caplog.handler)


def _settings(jwt: str, aes: str, debug: bool = False) -> SimpleNamespace:
    return SimpleNamespace(JWT_SECRET=jwt, AES_KEY=aes, DEBUG=debug)


def _strong() -> str:
    return secrets.token_urlsafe(48)


def _repo_placeholders() -> set[str]:
    """Every JWT_SECRET / AES_KEY value written anywhere in the repository."""
    values = {
        Settings.model_fields["JWT_SECRET"].default,
        Settings.model_fields["AES_KEY"].default,
        "test-secret-key-for-unit-tests",  # tests/conftest.py
        "test-aes-key-32-bytes-long-value",  # tests/conftest.py
    }
    pattern = re.compile(r"^\s*(?:JWT_SECRET|AES_KEY)\s*[:=]\s*(\S+)\s*$", re.M)
    for name in (".env.example", "docs/DEPLOYMENT.md", ".github/workflows/ci.yml"):
        values |= set(pattern.findall((REPO / name).read_text()))
    return values


def test_every_placeholder_in_the_repo_is_rejected():
    placeholders = _repo_placeholders()
    assert len(placeholders) >= 6
    for value in placeholders:
        assert secret_problems(_settings(value, _strong())), f"accepted JWT_SECRET {value!r}"
        assert secret_problems(_settings(_strong(), value)), f"accepted AES_KEY {value!r}"


def test_short_repetitive_and_shared_secrets_are_rejected():
    assert "JWT_SECRET is shorter than 32 characters" in secret_problems(_settings("s3cr3t", _strong()))
    assert any("repetitive" in p for p in secret_problems(_settings("a" * 40, _strong())))
    shared = _strong()
    assert "JWT_SECRET and AES_KEY must be different values" in secret_problems(_settings(shared, shared))


def test_generated_secrets_pass():
    for _ in range(50):
        assert secret_problems(_settings(_strong(), _strong())) == []


def test_production_refuses_to_start_without_leaking_the_secret():
    weak = "short-but-secret-123"
    with pytest.raises(InsecureSecretsError) as exc:
        enforce_secrets(_settings(weak, _strong(), debug=False))
    message = str(exc.value)
    assert "JWT_SECRET" in message and "token_urlsafe" in message
    assert weak not in message


def test_debug_only_warns(security_log):
    weak = "short-but-secret-123"
    enforce_secrets(_settings(weak, weak, debug=True))
    assert "Insecure secrets" in security_log.text
    assert weak not in security_log.text


def test_sound_secrets_start_silently(security_log):
    enforce_secrets(_settings(_strong(), _strong(), debug=False))
    assert security_log.text == ""
