"""
One way to call the language model, whichever provider runs it.

LLM_PROVIDER selects the provider:
- "ollama" (default): a local Ollama server at OLLAMA_BASE_URL, model OLLAMA_MODEL.
- "openai": any OpenAI-compatible chat-completions API -- Groq, OpenRouter,
  Cloudflare Workers AI, OpenAI -- at LLM_BASE_URL with LLM_API_KEY and
  LLM_MODEL. For Groq: LLM_BASE_URL=https://api.groq.com/openai/v1.

Prompts carry only de-identified data (lab values, age, sex, measurements,
goals, conditions); the prompt builders never include names, contact details
or the report file. Before a prompt leaves the server, email addresses and
phone numbers are redacted anyway, as a safety net.

Every failure raises LLMError; callers fall back to template plans.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time

import httpx

from app.core.config import settings

logger = logging.getLogger("nutrimed.llm")


class LLMError(Exception):
    """The model could not produce an answer (unreachable, rejected, rate limited...)."""


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# 10+ digits, optionally grouped: phone numbers. Lab values never look like this.
_PHONE_RE = re.compile(r"(?<!\d)\+?\d(?:[\s-]?\d){9,}(?!\d)")

#: Retries for rate limiting (429), the norm on free tiers.
_MAX_RETRIES = 2
_MAX_RETRY_WAIT_SECONDS = 20.0


def _is_external() -> bool:
    return settings.LLM_PROVIDER == "openai"


def model_name() -> str:
    """The model answering prompts, for logs and generation metrics."""
    return settings.LLM_MODEL if _is_external() else settings.OLLAMA_MODEL


def redact(prompt: str) -> str:
    """Remove email addresses and phone numbers from a prompt."""
    cleaned = _PHONE_RE.sub("[redacted]", _EMAIL_RE.sub("[redacted]", prompt))
    if cleaned != prompt:
        # A prompt builder included contact details: a bug worth hearing about.
        logger.warning("Redacted personal contact details from an LLM prompt")
    return cleaned


def _request(prompt: str) -> tuple[str, dict, dict]:
    if _is_external():
        if not (settings.LLM_BASE_URL and settings.LLM_API_KEY and settings.LLM_MODEL):
            raise LLMError("LLM_PROVIDER=openai needs LLM_BASE_URL, LLM_API_KEY and LLM_MODEL")
        return (
            f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
            {"Authorization": f"Bearer {settings.LLM_API_KEY}"},
            {
                "model": settings.LLM_MODEL,
                "messages": [{"role": "user", "content": redact(prompt)}],
                # Low randomness: the answers are JSON that is parsed and verified.
                "temperature": 0.2,
            },
        )
    return (
        f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
        {},
        {"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
    )


def _text(response: httpx.Response) -> str:
    data = response.json()
    try:
        if _is_external():
            return data["choices"][0]["message"]["content"] or ""
        return data.get("response", "")
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected response from the model API: {str(data)[:200]}") from exc


def _retry_wait(response: httpx.Response, attempt: int) -> float | None:
    """Seconds to wait before retrying, or None if the response is final."""
    if response.status_code != 429 or attempt >= _MAX_RETRIES:
        return None
    try:
        wait = float(response.headers.get("retry-after", ""))
    except ValueError:
        wait = 2.0 * (attempt + 1)
    return min(max(wait, 0.5), _MAX_RETRY_WAIT_SECONDS)


def _error(response: httpx.Response) -> LLMError:
    if response.status_code == 429:
        return LLMError("The model API is rate limiting requests (429)")
    return LLMError(f"The model API returned {response.status_code}: {response.text[:200]}")


def complete_sync(prompt: str) -> str:
    """The model's answer to a prompt (blocking; for Celery workers)."""
    url, headers, payload = _request(prompt)
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=settings.LLM_TIMEOUT_SECONDS)
        except httpx.HTTPError as exc:
            raise LLMError(f"Model API unreachable: {exc}") from exc
        wait = _retry_wait(response, attempt)
        if wait is not None:
            time.sleep(wait)
            continue
        if response.is_success:
            return _text(response)
        raise _error(response)
    raise LLMError("unreachable")  # pragma: no cover


async def complete(prompt: str) -> str:
    """The model's answer to a prompt (for request handlers)."""
    url, headers, payload = _request(prompt)
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await client.post(url, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                raise LLMError(f"Model API unreachable: {exc}") from exc
            wait = _retry_wait(response, attempt)
            if wait is not None:
                await asyncio.sleep(wait)
                continue
            if response.is_success:
                return _text(response)
            raise _error(response)
    raise LLMError("unreachable")  # pragma: no cover


async def readiness() -> tuple[dict, bool]:
    """(details, ok) for /health/ready: is the provider reachable and the model available?"""
    provider = "openai-compatible" if _is_external() else "ollama"
    details = {"provider": provider, "model": model_name()}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            if _is_external():
                resp = await client.get(
                    f"{settings.LLM_BASE_URL.rstrip('/')}/models",
                    headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
                )
                resp.raise_for_status()
                available = {m.get("id") for m in resp.json().get("data", [])}
            else:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
                resp.raise_for_status()
                available = {m.get("name") for m in resp.json().get("models", [])}
    except Exception as exc:
        return {**details, "status": f"unreachable: {exc}"}, False

    if model_name() in available:
        return {**details, "status": "ok"}, True
    return {**details, "status": "model_not_available", "available": sorted(a for a in available if a)[:20]}, False
