"""The provider-agnostic model client: Groq-style APIs, Ollama, retries, redaction."""

import httpx
import pytest

from app.core.config import settings
from app.services import llm_client


def _response(status: int, body: dict, headers: dict | None = None) -> httpx.Response:
    return httpx.Response(status, json=body, headers=headers, request=httpx.Request("POST", "http://test"))


@pytest.fixture()
def groq(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://api.groq.com/openai/v1/")
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(settings, "LLM_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setattr(llm_client.time, "sleep", lambda _s: None)


@pytest.fixture()
def calls(monkeypatch):
    """Record outgoing requests; tests queue the responses to return."""
    log: list[dict] = []
    queue: list[httpx.Response] = []

    def fake_post(url, json=None, headers=None, timeout=None):
        log.append({"url": url, "json": json, "headers": headers or {}})
        return queue.pop(0)

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    return log, queue


def test_openai_compatible_request_and_answer(groq, calls):
    log, queue = calls
    queue.append(_response(200, {"choices": [{"message": {"content": '[{"day": "Monday"}]'}}]}))

    assert llm_client.complete_sync("Plan meals") == '[{"day": "Monday"}]'
    sent = log[0]
    assert sent["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert sent["headers"]["Authorization"] == "Bearer test-key"
    assert sent["json"]["model"] == "llama-3.3-70b-versatile"
    assert sent["json"]["messages"] == [{"role": "user", "content": "Plan meals"}]
    assert llm_client.model_name() == "llama-3.3-70b-versatile"


def test_contact_details_never_leave_the_server(groq, calls):
    log, queue = calls
    queue.append(_response(200, {"choices": [{"message": {"content": "ok"}}]}))

    llm_client.complete_sync("Patient rahul@example.com, phone +91 98765 43210, hemoglobin 11.2, platelets 250000")
    content = log[0]["json"]["messages"][0]["content"]
    assert "rahul@example.com" not in content
    assert "98765" not in content
    # Lab values are untouched.
    assert "11.2" in content and "250000" in content


def test_rate_limit_is_retried(groq, calls):
    log, queue = calls
    queue.append(_response(429, {"error": "rate limited"}, headers={"retry-after": "1"}))
    queue.append(_response(200, {"choices": [{"message": {"content": "ok"}}]}))

    assert llm_client.complete_sync("hi") == "ok"
    assert len(log) == 2


def test_failures_raise_llm_error(groq, calls, monkeypatch):
    _log, queue = calls
    queue.extend([_response(429, {})] * 3)
    with pytest.raises(llm_client.LLMError, match="rate limiting"):
        llm_client.complete_sync("hi")

    queue.append(_response(500, {"error": "boom"}))
    with pytest.raises(llm_client.LLMError, match="500"):
        llm_client.complete_sync("hi")

    def unreachable(*_a, **_k):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(llm_client.httpx, "post", unreachable)
    with pytest.raises(llm_client.LLMError, match="unreachable"):
        llm_client.complete_sync("hi")


def test_missing_configuration_is_reported(groq, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    with pytest.raises(llm_client.LLMError, match="LLM_API_KEY"):
        llm_client.complete_sync("hi")


def test_ollama_is_the_default(monkeypatch, calls):
    log, queue = calls
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama")
    queue.append(_response(200, {"response": "ok"}))

    assert llm_client.complete_sync("hi") == "ok"
    assert log[0]["url"].endswith("/api/generate")
    assert log[0]["json"] == {"model": settings.OLLAMA_MODEL, "prompt": "hi", "stream": False}


@pytest.mark.asyncio
async def test_async_completion(groq, monkeypatch):
    async def fake_post(self, url, json=None, headers=None):
        return _response(200, {"choices": [{"message": {"content": "async ok"}}]})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    assert await llm_client.complete("hi") == "async ok"


@pytest.mark.asyncio
async def test_readiness_checks_the_model_is_available(groq, monkeypatch):
    async def fake_get(self, url, headers=None):
        assert url == "https://api.groq.com/openai/v1/models"
        return httpx.Response(
            200, json={"data": [{"id": "llama-3.3-70b-versatile"}]}, request=httpx.Request("GET", url)
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    details, ok = await llm_client.readiness()
    assert ok and details["status"] == "ok" and details["provider"] == "openai-compatible"

    monkeypatch.setattr(settings, "LLM_MODEL", "not-a-model")
    details, ok = await llm_client.readiness()
    assert not ok and details["status"] == "model_not_available"
