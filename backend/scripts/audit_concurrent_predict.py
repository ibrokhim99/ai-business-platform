"""Audit concurrent execution through PredictionService — the actual chat path.

Mimics what /chat/stream does: gathers many models concurrently with a semaphore,
times each one, flags anything slow or hung.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from app.config import settings
from app.core.redis_client import init_redis
from app.db.session import AsyncSessionLocal
from app.ml.registry import ModelRegistry
from app.services.prediction_service import PredictionService
from app.services.profile_to_input import ChatProfile, build as build_input


SLOW_S = 1.5
TIMEOUT_S = 20.0


@dataclass
class Result:
    model_id: str
    elapsed_s: float
    status: str
    note: str = ""


async def time_one(svc: PredictionService, mid: str, profile: ChatProfile) -> Result:
    t0 = time.perf_counter()
    try:
        inp = build_input(mid, profile)
        await asyncio.wait_for(
            svc.predict(mid, inp, include_explanation=False, request_id=f"audit:{mid}", user_id="audit", user_role="admin"),
            timeout=TIMEOUT_S,
        )
        elapsed = time.perf_counter() - t0
        if elapsed > SLOW_S:
            return Result(mid, elapsed, "slow")
        return Result(mid, elapsed, "ok")
    except asyncio.TimeoutError:
        return Result(mid, TIMEOUT_S, "timeout", f"killed after {TIMEOUT_S}s")
    except Exception as e:
        return Result(mid, time.perf_counter() - t0, "error", f"{type(e).__name__}: {e}"[:200])


async def main() -> int:
    reg = ModelRegistry()
    ids = sorted(reg.all_ids())

    # Initialize Redis (matches main.py behaviour)
    try:
        redis = await init_redis()
    except Exception:
        redis = None

    # Get a DB session for prediction logging
    async with AsyncSessionLocal() as db:
        svc = PredictionService(reg, redis, db)
        profile = ChatProfile(
            region_id="tashkent-01",
            mcc_code="5812",
            monthly_revenue_estimate=15_000,
            initial_investment=50_000,
        )

        # Use the same concurrency as the chat path
        sem = asyncio.Semaphore(max(1, settings.chat_model_concurrency))

        async def gated(mid: str) -> Result:
            async with sem:
                return await time_one(svc, mid, profile)

        print(f"audit: {len(ids)} models concurrently (semaphore={settings.chat_model_concurrency}), timeout={TIMEOUT_S}s")
        print()
        t0 = time.perf_counter()
        results = await asyncio.gather(*(gated(mid) for mid in ids))
        elapsed = time.perf_counter() - t0

    # Sort by elapsed
    for r in sorted(results, key=lambda x: -x.elapsed_s):
        marker = {"ok": "✓", "slow": "⚠", "timeout": "✗", "error": "✗"}[r.status]
        print(f"  {marker} {r.model_id:6s} {r.elapsed_s:6.2f}s  {r.status:7s} {r.note}")

    print()
    slow = [r for r in results if r.status == "slow"]
    timeouts = [r for r in results if r.status == "timeout"]
    errors = [r for r in results if r.status == "error"]
    print(f"summary: total wall {elapsed:.2f}s, ok={len(results)-len(slow)-len(timeouts)-len(errors)}, slow={len(slow)}, timeouts={len(timeouts)}, errors={len(errors)}")

    return 0 if not (timeouts or errors) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
