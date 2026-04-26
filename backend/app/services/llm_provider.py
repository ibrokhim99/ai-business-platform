"""
LLM provider selector — picks Ollama or OpenAI based on settings.llm_provider.

Both clients expose the same `chat`, `chat_stream`, `health`, and `model`
surface, so LlmChatService doesn't care which one it gets.
"""
from __future__ import annotations

from typing import Protocol, Any, AsyncIterator

from app.config import settings
from app.services.ollama_client import get_ollama_client, OllamaClient
from app.services.openai_client import get_openai_client, OpenAIClient


class LlmClient(Protocol):
    @property
    def model(self) -> str: ...

    async def health(self) -> bool: ...

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]: ...

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]: ...


def get_llm_client() -> LlmClient:
    provider = (settings.llm_provider or "ollama").lower()
    if provider == "openai":
        return get_openai_client()
    return get_ollama_client()
