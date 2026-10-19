"""Settings that hosting platforms fill in (see render.yaml)."""

import re

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(**values) -> Settings:
    return Settings(_env_file=None, **values)


class TestOcrServiceUrl:
    def test_adds_a_scheme_to_a_private_network_address(self):
        # Render's fromService hostport: host and port only.
        assert _settings(OCR_SERVICE_URL="nutrimed-ocr-a1b2:8001").OCR_SERVICE_URL == "http://nutrimed-ocr-a1b2:8001"

    def test_keeps_a_full_url(self):
        assert _settings(OCR_SERVICE_URL="https://ocr.example.com/").OCR_SERVICE_URL == "https://ocr.example.com"
        assert _settings().OCR_SERVICE_URL == "http://localhost:8001"


class TestAllowedOriginRegex:
    # The example in config.py and docs/DEPLOY_RENDER_VERCEL.md.
    EXAMPLE = r"^https://nutrimed-[a-z0-9-]+-your-team\.vercel\.app$"

    def test_documented_example_matches_preview_urls_only(self):
        pattern = re.compile(_settings(ALLOWED_ORIGIN_REGEX=self.EXAMPLE).ALLOWED_ORIGIN_REGEX)
        assert pattern.fullmatch("https://nutrimed-git-fix-login-your-team.vercel.app")
        assert pattern.fullmatch("https://nutrimed-4k2j9x1-your-team.vercel.app")
        assert not pattern.fullmatch("https://nutrimed-4k2j9x1-other-team.vercel.app")
        assert not pattern.fullmatch("http://nutrimed-4k2j9x1-your-team.vercel.app")
        assert not pattern.fullmatch("https://evil.example/https://nutrimed-x-your-team.vercel.app")

    def test_rejects_an_invalid_pattern_at_startup(self):
        with pytest.raises(ValidationError, match="ALLOWED_ORIGIN_REGEX"):
            _settings(ALLOWED_ORIGIN_REGEX="^https://(unclosed")

    def test_is_passed_to_cors(self):
        from starlette.middleware.cors import CORSMiddleware

        from app.core.config import settings
        from app.main import app

        cors = next(m for m in app.user_middleware if m.cls is CORSMiddleware)
        assert cors.kwargs["allow_origin_regex"] == (settings.ALLOWED_ORIGIN_REGEX or None)


def test_client_ip_hops_must_be_positive():
    with pytest.raises(ValidationError, match="CLIENT_IP_HOPS"):
        _settings(CLIENT_IP_HOPS=0)


def test_api_docs_follow_debug():
    from app.core.config import settings
    from app.main import app

    expected = "/docs" if settings.DEBUG else None
    assert app.docs_url == expected
    assert (app.openapi_url is None) == (not settings.DEBUG)
