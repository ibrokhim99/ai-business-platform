"""
PredictionService — orchestrates model lookup, Redis cache, prediction, SHAP, and DB audit log.

Every API endpoint delegates to this service.
Cache key: sha256(model_id + version + explain_flag + sorted_input_json)
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.ml.base import PredictionResult
from app.ml.explainability import get_explainability_service
from app.ml.registry import ModelRegistry

log = get_logger()

# Cache TTL per block (seconds)
_BLOCK_TTL: dict[str, int] = {
    "A": settings.cache_ttl_block_a,
    "B": settings.cache_ttl_block_b,
    "C": settings.cache_ttl_block_c,
    "D": settings.cache_ttl_block_d,
    "E": settings.cache_ttl_block_e,
    "F": settings.cache_ttl_block_f,
    "G": settings.cache_ttl_block_g,
    "H": settings.cache_ttl_block_h,
    "I": settings.cache_ttl_block_i,
    "J": settings.cache_ttl_block_j,
}
# These models are always live — never cache.
# All Block J (fraud) models bypass the cache so signals reflect the latest state.
_NO_CACHE: set[str] = {
    "M-C2", "M-G2",
    "M-J1", "M-J2", "M-J3", "M-J4", "M-J5",
}


class PredictionService:
    def __init__(
        self,
        registry: ModelRegistry,
        redis_client: aioredis.Redis | None = None,
        db: AsyncSession | None = None,
    ):
        self._registry = registry
        self._redis = redis_client
        self._db = db
        self._explainability = get_explainability_service()

    async def predict(
        self,
        model_id: str,
        input_data: BaseModel,
        include_explanation: bool = False,
        version: str = "latest",
        request_id: str | None = None,
        user_id: str | None = None,
        user_role: str | None = None,
    ) -> PredictionResult:
        if request_id is None:
            request_id = str(uuid.uuid4())

        model = self._registry.get(model_id, version)
        cache_key = None
        cache_hit = False

        # ── Redis cache check ──────────────────────────────────────────────────
        if self._redis and model_id not in _NO_CACHE:
            cache_key = self._build_cache_key(model_id, version, input_data, include_explanation)
            try:
                cached = await self._redis.get(cache_key)
                if cached:
                    result = PredictionResult.model_validate_json(cached)
                    result.request_id = request_id
                    cache_hit = True
                    log.debug("cache_hit", model_id=model_id)
                    return result
            except Exception as e:
                log.warning("redis_get_error", model_id=model_id, error=str(e))

        # ── Run prediction ─────────────────────────────────────────────────────
        result = model.to_prediction_result(input_data, include_explanation, request_id)

        # Attach real SHAP explanation for non-stub models
        if include_explanation and not model.metadata.is_stub:
            result.explanation = self._explainability.explain(model, input_data)

        # ── Write to Redis ─────────────────────────────────────────────────────
        if self._redis and cache_key:
            ttl = _BLOCK_TTL.get(model.metadata.block, 21600)
            try:
                await self._redis.setex(cache_key, ttl, result.model_dump_json())
            except Exception as e:
                log.warning("redis_set_error", model_id=model_id, error=str(e))

        # ── Async DB audit log ─────────────────────────────────────────────────
        if self._db:
            await self._write_audit_log(
                model_id=model_id,
                model_version=result.version,
                input_data=input_data,
                result=result,
                cache_hit=cache_hit,
                request_id=request_id,
                user_id=user_id,
                user_role=user_role,
            )

        log.info(
            "prediction",
            model_id=model_id,
            latency_ms=result.latency_ms,
            is_stub=result.is_stub,
            cache_hit=cache_hit,
        )
        return result

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _build_cache_key(
        self, model_id: str, version: str, input_data: BaseModel, explain: bool
    ) -> str:
        raw = json.dumps(
            {"mid": model_id, "v": version, "ex": explain, "in": input_data.model_dump()},
            sort_keys=True, default=str,
        )
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return f"pred:{model_id}:{version}:{digest}"

    async def _write_audit_log(
        self,
        *,
        model_id: str,
        model_version: str,
        input_data: BaseModel,
        result: PredictionResult,
        cache_hit: bool,
        request_id: str,
        user_id: str | None,
        user_role: str | None,
    ) -> None:
        try:
            from app.models.audit import PredictionLog
            log_entry = PredictionLog(
                model_id=model_id,
                model_version=model_version,
                user_id=int(user_id) if user_id and user_id.isdigit() else None,
                user_role=user_role,
                input_hash=hashlib.sha256(
                    json.dumps(input_data.model_dump(), sort_keys=True, default=str).encode()
                ).hexdigest(),
                input_snapshot=input_data.model_dump(),
                output_snapshot=result.prediction if isinstance(result.prediction, dict) else {},
                latency_ms=result.latency_ms,
                is_stub=result.is_stub,
                cache_hit=cache_hit,
                request_id=request_id,
            )
            self._db.add(log_entry)
            await self._db.flush()
        except Exception as e:
            log.warning("audit_log_error", error=str(e))
            # Rollback so the session is clean for the rest of the request.
            try:
                await self._db.rollback()
            except Exception:
                pass
