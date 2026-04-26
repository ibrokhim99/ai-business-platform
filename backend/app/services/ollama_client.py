"""
Async client for a local Ollama server (default http://localhost:11434).

Thin wrapper over httpx — only the surface we need:
- chat()        : non-streaming, returns the full Ollama JSON response
- chat_stream() : async iterator yielding decoded JSON chunks from /api/chat
- health()      : lightweight probe, used at app startup
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from app.config import settings
from app.core.logging import get_logger

log = get_logger()


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout_s: int | None = None,
    ):
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = default_model or settings.ollama_model
        self._timeout = timeout_s or settings.ollama_timeout_s

    @property
    def model(self) -> str:
        return self._model

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                if resp.status_code != 200:
                    return False
                tags = resp.json().get("models") or []
                names = [m.get("name", "") for m in tags]
                return any(n.startswith(self._model.split(":")[0]) for n in names)
        except Exception as e:
            log.warning("ollama_health_failed", error=str(e), base_url=self._base_url)
            return False

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        format: str | dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model or self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": settings.ollama_temperature,
                "num_ctx": settings.ollama_num_ctx,
                **(options or {}),
            },
        }
        if tools:
            payload["tools"] = tools
        if format is not None:
            payload["format"] = format

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            if resp.status_code >= 400:
                raise OllamaError(f"Ollama chat failed {resp.status_code}: {resp.text[:300]}")
            return resp.json()

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": model or self._model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": settings.ollama_temperature,
                "num_ctx": settings.ollama_num_ctx,
                **(options or {}),
            },
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    raise OllamaError(f"Ollama chat_stream failed {resp.status_code}: {body[:300]!r}")
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        log.warning("ollama_stream_bad_json", line=line[:200])


_client: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
