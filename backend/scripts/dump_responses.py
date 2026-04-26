"""Dump the full backend response for each model so I can write proper frontend mappings."""
from __future__ import annotations

import asyncio
import json
import httpx

from app.ml.registry import ModelRegistry
from app.services.profile_to_input import build, ChatProfile

BASE = "http://localhost:8000/api/v1"
TARGETS = ["M-A6", "M-B1", "M-B2", "M-B3", "M-B4", "M-B6", "M-C3", "M-D1",
           "M-D5", "M-E1", "M-E2", "M-F1", "M-F4", "M-F5", "M-G2", "M-G3"]


async def main():
    async with httpx.AsyncClient(timeout=30.0) as cli:
        r = await cli.post(f"{BASE}/auth/token", json={"email": "admin@bank.uz", "password": "admin123"})
        token = r.json()["access_token"]

        # Discover routes
        spec = (await cli.get("http://localhost:8000/openapi.json")).json()
        block_prefixes = {"market-analysis": "A", "forecasting": "B", "location": "C", "financial": "D",
                          "competition": "E", "credit": "F", "social": "G", "marketing": "H",
                          "operations": "I", "fraud": "J"}
        routes_by_block: dict[str, list[str]] = {b: [] for b in block_prefixes.values()}
        for path, methods in spec.get("paths", {}).items():
            if "post" not in methods:
                continue
            for prefix, block in block_prefixes.items():
                if path.startswith(f"/api/v1/{prefix}/"):
                    routes_by_block[block].append(path.replace("/api/v1", ""))
                    break
        endpoint_by_mid: dict[str, str] = {}
        for block, routes in routes_by_block.items():
            for i, route in enumerate(routes, 1):
                endpoint_by_mid[f"M-{block}{i}"] = route

        reg = ModelRegistry()
        profile = ChatProfile(region_id="tashkent-01", mcc_code="5812",
                              monthly_revenue_estimate=15_000, initial_investment=50_000)

        for mid in TARGETS:
            inp = build(mid, profile)
            payload = inp.model_dump() if hasattr(inp, "model_dump") else dict(inp)
            r = await cli.post(
                f"{BASE}{endpoint_by_mid[mid]}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            body = r.json()
            pred = body.get("prediction") or body
            print(f"\n=== {mid} → {endpoint_by_mid[mid]} ===")
            print(json.dumps(pred, indent=2, default=str)[:1500])


if __name__ == "__main__":
    asyncio.run(main())
