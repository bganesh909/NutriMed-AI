import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class OllamaClient:
    """Async client for the Ollama REST API with retry logic."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_base_delay: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.REQUEST_TIMEOUT
        self.max_retries = max_retries or settings.MAX_RETRIES
        self.retry_base_delay = retry_base_delay or settings.RETRY_BASE_DELAY
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request_with_retry(
        self, method: str, path: str, **kwargs
    ) -> httpx.Response:
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                client = await self._get_client()
                response = await client.request(method, path, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                last_exception = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                    raise
                delay = self.retry_base_delay * (2 ** attempt)
                logger.warning(
                    "Ollama request failed (attempt %d/%d): %s. Retrying in %.1fs",
                    attempt + 1,
                    self.max_retries,
                    str(exc),
                    delay,
                )
                await asyncio.sleep(delay)
        raise last_exception

    async def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> dict:
        """Generate a completion from the model."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        if system_prompt:
            payload["system"] = system_prompt
        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        start = time.monotonic()
        response = await self._request_with_retry("POST", "/api/generate", json=payload)
        elapsed_ms = (time.monotonic() - start) * 1000

        data = response.json()
        return {
            "text": data.get("response", ""),
            "model": data.get("model", model),
            "tokens_used": data.get("eval_count", 0),
            "duration_ms": round(elapsed_ms, 2),
            "done": data.get("done", True),
        }

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a completion from the model."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt
        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        client = await self._get_client()
        async with client.stream("POST", "/api/generate", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

    async def chat(
        self,
        model: str,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """Send a chat completion request."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        start = time.monotonic()
        response = await self._request_with_retry("POST", "/api/chat", json=payload)
        elapsed_ms = (time.monotonic() - start) * 1000

        data = response.json()
        message = data.get("message", {})
        return {
            "text": message.get("content", ""),
            "model": data.get("model", model),
            "role": message.get("role", "assistant"),
            "tokens_used": data.get("eval_count", 0),
            "duration_ms": round(elapsed_ms, 2),
        }

    async def list_models(self) -> list[dict]:
        """List all locally available models."""
        response = await self._request_with_retry("GET", "/api/tags")
        data = response.json()
        models = []
        for m in data.get("models", []):
            models.append({
                "name": m.get("name", ""),
                "size": self._format_size(m.get("size", 0)),
                "modified_at": m.get("modified_at", ""),
                "digest": m.get("digest", ""),
            })
        return models

    async def pull_model(self, name: str) -> dict:
        """Pull a model from the Ollama registry."""
        response = await self._request_with_retry(
            "POST", "/api/pull", json={"name": name, "stream": False}
        )
        return response.json()

    async def is_healthy(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            client = await self._get_client()
            response = await client.get("/")
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes == 0:
            return "0B"
        units = ["B", "KB", "MB", "GB", "TB"]
        idx = 0
        size = float(size_bytes)
        while size >= 1024 and idx < len(units) - 1:
            size /= 1024
            idx += 1
        return f"{size:.1f}{units[idx]}"


# Module-level singleton
_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
