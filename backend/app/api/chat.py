"""LLM-driven chat endpoint backed by qwen2.5 (via Ollama) + 55 ML models.

Streams Server-Sent Events as the LLM picks tools, runs models, and
synthesizes the final Uzbek answer.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.dependencies import RegistryDep, RedisDep, DBDep, UserDep
from app.services.llm_chat_service import ChatTurn, LlmChatService
from app.services.llm_provider import get_llm_client
from app.services.prediction_service import PredictionService
from app.services.profile_to_input import ChatProfile

router = APIRouter(prefix="/chat", tags=["Chat (LLM)"])


class ChatTurnIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatTurnIn] = Field(default_factory=list)
    profile: ChatProfile = Field(default_factory=ChatProfile)


@router.post("/stream", summary="Streamed chat response (SSE)")
async def chat_stream(
    body: ChatRequest,
    registry: RegistryDep,
    redis: RedisDep,
    db: DBDep,
    user: UserDep,
):
    svc = LlmChatService(
        registry=registry,
        ollama=get_llm_client(),
        prediction_service=PredictionService(registry, redis, db),
    )

    history = [ChatTurn(role=t.role, content=t.content) for t in body.history]

    async def event_gen():
        async for ev in svc.stream_reply(
            user_message=body.message,
            history=history,
            profile=body.profile,
            user_id=user.user_id,
            user_role=user.role,
        ):
            yield ev.to_sse()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
