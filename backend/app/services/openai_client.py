"""
Async OpenAI client — same surface as OllamaClient so LlmChatService works
unchanged regardless of provider.

The two methods that matter (`chat`, `chat_stream`) translate the OpenAI
response shape into the Ollama-style dict the chat service already consumes:

    {"message": {"content": str, "tool_calls": [{"function": {"name", "arguments"}}]}}

OpenAI's wire format differs (`choices[0].message.tool_calls` with stringified
JSON arguments) — we normalize on the way out so the service stays uniform.
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from app.config import settings
from app.core.logging import get_logger

log = get_logger()


class OpenAIError(RuntimeError):
    pass


class OpenAIClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout_s: int | None = None,
    ):
        self._api_key = api_key or settings.openai_api_key
        self._base_url = (base_url or settings.openai_base_url).rstrip("/")
        self._model = default_model or settings.openai_model
        self._timeout = timeout_s or settings.openai_timeout_s
        if not self._api_key:
            log.warning("openai_no_api_key", note="OPENAI_API_KEY is empty — chat will fail")

    @property
    def model(self) -> str:
        return self._model

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def health(self) -> bool:
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/models", headers=self._headers())
                return resp.status_code == 200
        except Exception as e:
            log.warning("openai_health_failed", error=str(e), base_url=self._base_url)
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
        # Strip Ollama-specific tool message structure if any.
        payload: dict[str, Any] = {
            "model": model or self._model,
            "messages": _normalize_messages(messages),
            "stream": False,
            "temperature": (options or {}).get("temperature", settings.openai_temperature),
        }
        if tools:
            payload["tools"] = tools
        # OpenAI doesn't have an exact equivalent of Ollama's `format=json`,
        # but `response_format={"type":"json_object"}` is close. We only set it
        # when explicitly requested.
        if format == "json" or (isinstance(format, dict) and format.get("type") == "json_object"):
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            if resp.status_code >= 400:
                raise OpenAIError(f"OpenAI chat failed {resp.status_code}: {resp.text[:300]}")
            return _to_ollama_shape(resp.json())

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
            "messages": _normalize_messages(messages),
            "stream": True,
            "temperature": (options or {}).get("temperature", settings.openai_temperature),
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            ) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    raise OpenAIError(f"OpenAI chat_stream failed {resp.status_code}: {body[:300]!r}")
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        yield {"message": {"content": ""}, "done": True}
                        return
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        log.warning("openai_stream_bad_json", line=line[:200])
                        continue
                    delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
                    yield {
                        "message": {"content": delta.get("content") or ""},
                        "done": False,
                    }


def _normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """OpenAI rejects roles other than system/user/assistant/tool/function.
    The Ollama path uses role='tool' with raw content; OpenAI requires
    `tool_call_id` on tool messages. Where tool_call_id is missing, downgrade
    the message to role='user' so the call still goes through.
    """
    out: list[dict[str, Any]] = []
    for m in messages:
        if m.get("role") == "tool" and "tool_call_id" not in m:
            out.append({"role": "user", "content": m.get("content", "")})
        else:
            out.append(m)
    return out


def _to_ollama_shape(resp: dict[str, Any]) -> dict[str, Any]:
    """Convert an OpenAI chat-completion response to the Ollama dict shape
    LlmChatService expects: `{"message": {"content": ..., "tool_calls": [...]}}`.
    Tool-call arguments come back as a JSON string from OpenAI; LlmChatService
    handles both string and dict, so we leave them as-is.
    """
    choice = (resp.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    tool_calls_raw = msg.get("tool_calls") or []
    tool_calls: list[dict[str, Any]] = []
    for tc in tool_calls_raw:
        fn = tc.get("function") or {}
        tool_calls.append({
            "function": {
                "name": fn.get("name"),
                "arguments": fn.get("arguments"),  # string, parsed downstream
            },
        })
    return {
        "message": {
            "content": msg.get("content") or "",
            "tool_calls": tool_calls,
        },
    }


_client: OpenAIClient | None = None


def get_openai_client() -> OpenAIClient:
    global _client
    if _client is None:
        _client = OpenAIClient()
    return _client
