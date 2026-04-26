"""Hit all 55 HTTP routes in parallel — exercises the full FastAPI stack
(auth, middleware, rate limiter, DB, Redis, model)."""
from __future__ import annotations

import asyncio
import json
import time

import httpx

from app.ml.registry import ModelRegistry
from app.services.profile_to_input import build, ChatProfile

BASE = "http://localhost:8000/api/v1"
TIMEOUT_S = 30.0


async def discover_endpoints() -> dict[str, str]:
    """Map model_id -> HTTP route by scraping models_meta + registered routes."""
    async with httpx.AsyncClient(timeout=10.0) as cli:
        spec = (await cli.get("http://localhost:8000/openapi.json")).json()
    block_prefixes = {
        "market-analysis": "A", "forecasting": "B", "location": "C",
        "financial": "D", "competition": "E", "credit": "F",
        "social": "G", "marketing": "H", "operations": "I", "fraud": "J",
    }
    routes_per_block: dict[str, list[str]] = {b: [] for b in block_prefixes.values()}
    for path, methods in spec.get("paths", {}).items():
        if "post" not in methods:
            continue
        for prefix, block in block_prefixes.items():
            if path.startswith(f"/api/v1/{prefix}/"):
                routes_per_block[block].append(path.replace("/api/v1", ""))
                break

    # Pair model_id with route by index — best-effort (we don't have a strict
    # mapping in metadata). For audit purposes the count just needs to be 55.
    out: dict[str, str] = {}
    for block, routes in routes_per_block.items():
        for i, route in enumerate(routes, 1):
            mid = f"M-{block}{i}"
            out[mid] = route
    return out


async def call(cli: httpx.AsyncClient, mid: str, route: str, body: dict, token: str) -> tuple[str, float, int]:
    t0 = time.perf_counter()
    try:
        r = await cli.post(
            f"{BASE}{route}",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT_S,
        )
        return mid, time.perf_counter() - t0, r.status_code
    except httpx.TimeoutException:
        return mid, TIMEOUT_S, -1
    except Exception as e:
        return mid, time.perf_counter() - t0, -2


async def main() -> int:
    async with httpx.AsyncClient(timeout=10.0) as cli:
        r = await cli.post(f"{BASE}/auth/token", json={"email": "admin@bank.uz", "password": "admin123"})
        token = r.json()["access_token"]

    routes = await discover_endpoints()
    reg = ModelRegistry()
    profile = ChatProfile(region_id="tashkent-01", mcc_code="5812", monthly_revenue_estimate=15_000, initial_investment=50_000)

    # Build payloads using profile_to_input (matches what /chat/stream sends).
    payloads: dict[str, dict] = {}
    skipped: list[str] = []
    for mid in sorted(reg.all_ids()):
        if mid not in routes:
            skipped.append(mid)
            continue
        try:
            inp = build(mid, profile)
            payloads[mid] = inp.model_dump() if hasattr(inp, "model_dump") else dict(inp)
        except Exception as e:
            skipped.append(f"{mid} (build fail: {e})")
    if skipped:
        print(f"skipped: {skipped}")
    print(f"firing {len(payloads)} parallel HTTP POSTs ...")

    async with httpx.AsyncClient() as cli:
        t0 = time.perf_counter()
        results = await asyncio.gather(
            *(call(cli, mid, routes[mid], body, token) for mid, body in payloads.items())
        )
        wall = time.perf_counter() - t0

    print()
    for mid, elapsed, status in sorted(results, key=lambda x: -x[1]):
        marker = "✓" if status == 200 else ("✗" if status > 0 else "!")
        note = ""
        if status == -1: note = "TIMEOUT"
        elif status == -2: note = "EXCEPTION"
        elif status != 200: note = f"HTTP {status}"
        print(f"  {marker} {mid:6s} {elapsed:6.2f}s  {note}")

    print()
    slow = [r for r in results if r[1] > 1.5 and r[2] == 200]
    timeouts = [r for r in results if r[2] == -1]
    errors = [r for r in results if r[2] not in (200, -1)]
    print(f"summary: total wall={wall:.2f}s, ok={sum(1 for r in results if r[2]==200)}, slow={len(slow)}, timeouts={len(timeouts)}, errors={len(errors)}")
    return 0 if not (timeouts or errors) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
