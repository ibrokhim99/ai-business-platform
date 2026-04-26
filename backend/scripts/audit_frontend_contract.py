"""Verify backend responses contain the fields the frontend tries to read.

For each model:
  1. Hits the backend HTTP endpoint with a default-profile payload.
  2. Captures the prediction dict's keys (recursively for one level of nesting).
  3. Parses frontend/src/lib/chat/models.ts to extract `r.X` field accesses
     inside that model's formatHeadline + buildSpark.
  4. Flags every frontend access path where NO option resolves to a key
     present in the backend response — that's a contract gap.

Output: a table per model with status:
  ✓ all frontend accesses resolve
  ⚠ at least one access falls through ALL `??` options → frontend reads `0` /
    `undefined` and the card may render zero values
  ✗ HTTP error
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from app.ml.registry import ModelRegistry
from app.services.profile_to_input import build, ChatProfile

BASE = "http://localhost:8000/api/v1"
MODELS_TS = Path("/app/../frontend/src/lib/chat/models.ts")
# But /app is mounted from ./backend; frontend is at host ./frontend, not in container.
# Read via shared bind: try a few candidates.
CANDIDATE_PATHS = [
    Path("/tmp/models.ts"),
    Path("/app/../frontend/src/lib/chat/models.ts"),
    Path("/frontend/src/lib/chat/models.ts"),
]


def find_models_ts() -> str | None:
    for p in CANDIDATE_PATHS:
        if p.exists():
            return p.read_text()
    return None


def parse_field_accesses(ts_src: str) -> dict[str, dict[str, list[list[str]]]]:
    """Return {model_id: {"headline": [[opt1, opt2, ...], ...], "spark": [...]}}.

    Each inner list is a chain of fallback names the frontend tries (the `r.x ?? r.y`
    pattern). A model is "wired correctly" if at least one option per chain is
    present in the backend response.
    """
    out: dict[str, dict[str, list[list[str]]]] = {}

    # Match each model object: starts with "modelId: 'M-XN'" and ends at the next
    # modelId or block boundary. We find each {} block.
    # Simpler: split on "modelId: '" and process each chunk.
    chunks = re.split(r"modelId:\s*'(M-[A-J][0-9]+)'", ts_src)
    # chunks[0] is preamble, then alternating (mid, body)
    for i in range(1, len(chunks), 2):
        mid = chunks[i]
        body = chunks[i + 1]
        # cap body at next modelId or end of array
        end = body.find("\n  },")  # end of model object
        if end > 0:
            body = body[:end]

        # Extract formatHeadline and buildSpark blocks
        out[mid] = {"headline": [], "spark": []}
        for kind, key in (("headline", "formatHeadline"), ("spark", "buildSpark")):
            m = re.search(rf"{key}:\s*\(([a-zA-Z_]+)\)\s*=>\s*", body)
            if not m:
                continue
            varname = m.group(1)
            # Extract the function body — go from `=>` to matching closing brace/paren.
            start = m.end()
            depth = 0
            in_arrow = False
            j = start
            while j < len(body):
                ch = body[j]
                if ch in "({": depth += 1
                elif ch in ")}":
                    depth -= 1
                    if depth <= 0:
                        break
                j += 1
            fn_body = body[start:j]
            # Find every `var.X` chain, including `??`-separated alternatives.
            # Pattern: `varname.field` and group consecutive `??` chains.
            chain_pattern = re.compile(
                rf"\b{varname}\.([a-zA-Z_][a-zA-Z_0-9]*)"
                rf"(?:\s*\?\?\s*{varname}\.([a-zA-Z_][a-zA-Z_0-9]*))*",
                re.MULTILINE,
            )
            # Simpler: find each `varname.X` and groups of `?? varname.Y` after.
            # Walk linearly.
            access_chains: list[list[str]] = []
            pos = 0
            while pos < len(fn_body):
                m2 = re.search(rf"{varname}\.([a-zA-Z_][a-zA-Z_0-9]*)", fn_body[pos:])
                if not m2:
                    break
                start_of_match = pos + m2.start()
                first_field = m2.group(1)
                chain = [first_field]
                # After this match, look for `?? var.Y ?? var.Z ...`
                tail_pos = pos + m2.end()
                while True:
                    m3 = re.match(rf"\s*\?\?\s*{varname}\.([a-zA-Z_][a-zA-Z_0-9]*)", fn_body[tail_pos:])
                    if not m3:
                        break
                    chain.append(m3.group(1))
                    tail_pos += m3.end()
                access_chains.append(chain)
                pos = tail_pos
            out[mid][kind] = access_chains
    return out


async def get_token(cli: httpx.AsyncClient) -> str:
    r = await cli.post(f"{BASE}/auth/token", json={"email": "admin@bank.uz", "password": "admin123"})
    r.raise_for_status()
    return r.json()["access_token"]


async def discover_routes() -> dict[str, list[str]]:
    async with httpx.AsyncClient(timeout=10.0) as cli:
        spec = (await cli.get("http://localhost:8000/openapi.json")).json()
    block_prefixes = {"market-analysis": "A", "forecasting": "B", "location": "C", "financial": "D",
                      "competition": "E", "credit": "F", "social": "G", "marketing": "H",
                      "operations": "I", "fraud": "J"}
    routes: dict[str, list[str]] = {b: [] for b in block_prefixes.values()}
    for path, methods in spec.get("paths", {}).items():
        if "post" not in methods:
            continue
        for prefix, block in block_prefixes.items():
            if path.startswith(f"/api/v1/{prefix}/"):
                routes[block].append(path.replace("/api/v1", ""))
                break
    return routes


def keys_in(obj: Any, prefix: str = "", max_depth: int = 2) -> set[str]:
    """Collect every dotted key path in obj up to max_depth, plus top-level names."""
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            if max_depth > 0:
                for sub in keys_in(v, k, max_depth - 1):
                    keys.add(sub)
    return keys


async def main() -> int:
    ts_src = find_models_ts()
    if not ts_src:
        print("ERROR: Cannot find frontend/src/lib/chat/models.ts inside container.")
        print("This script needs the frontend file mounted.")
        return 2

    accesses = parse_field_accesses(ts_src)
    print(f"parsed accesses for {len(accesses)} frontend models")

    routes_by_block = await discover_routes()
    reg = ModelRegistry()
    profile = ChatProfile(region_id="tashkent-01", mcc_code="5812",
                          monthly_revenue_estimate=15_000, initial_investment=50_000)

    async with httpx.AsyncClient(timeout=30.0) as cli:
        token = await get_token(cli)

        # Pair each model_id with first available route in its block.
        # Better: walk block routes in catalog order — they should match M-X1..M-XN.
        endpoint_by_mid: dict[str, str] = {}
        for block, routes in routes_by_block.items():
            for i, route in enumerate(routes, 1):
                mid = f"M-{block}{i}"
                endpoint_by_mid[mid] = route

        results: list[dict[str, Any]] = []
        for mid in sorted(reg.all_ids()):
            if mid not in endpoint_by_mid:
                results.append({"mid": mid, "status": "no_route"})
                continue
            try:
                inp = build(mid, profile)
                payload = inp.model_dump() if hasattr(inp, "model_dump") else dict(inp)
            except Exception as e:
                results.append({"mid": mid, "status": "build_fail", "err": str(e)})
                continue
            try:
                r = await cli.post(
                    f"{BASE}{endpoint_by_mid[mid]}",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=15.0,
                )
                if r.status_code != 200:
                    results.append({"mid": mid, "status": "http_error", "code": r.status_code,
                                    "body": r.text[:200]})
                    continue
                body = r.json()
                pred = body.get("prediction") or body
                resp_keys = keys_in(pred)
                fe = accesses.get(mid, {"headline": [], "spark": []})
                # For each chain: does at least one option match a backend key?
                missing_chains: list[list[str]] = []
                for kind in ("headline", "spark"):
                    for chain in fe[kind]:
                        if not any(c in resp_keys for c in chain):
                            missing_chains.append(chain)
                results.append({
                    "mid": mid, "status": "ok" if not missing_chains else "contract_gap",
                    "missing": missing_chains,
                    "frontend_chains": [c for kind in ("headline", "spark") for c in fe[kind]],
                    "backend_keys_sample": sorted(resp_keys)[:15],
                })
            except Exception as e:
                results.append({"mid": mid, "status": "exception", "err": str(e)})

    # Report
    print()
    print("=" * 80)
    print("CONTRACT REPORT")
    print("=" * 80)
    ok = [r for r in results if r["status"] == "ok"]
    gaps = [r for r in results if r["status"] == "contract_gap"]
    others = [r for r in results if r["status"] not in ("ok", "contract_gap")]
    print(f"  ok:           {len(ok)}/55")
    print(f"  contract gap: {len(gaps)}/55")
    print(f"  other issues: {len(others)}/55")
    if gaps:
        print()
        print("=== CONTRACT GAPS (frontend reads fields backend never returns) ===")
        for r in gaps:
            print(f"\n  {r['mid']}: missing chains = {r['missing']}")
            print(f"    backend returned keys: {r['backend_keys_sample']}")
    if others:
        print()
        print("=== OTHER ISSUES ===")
        for r in others:
            print(f"  {r['mid']}: {r['status']} {r}")

    return 0 if not gaps and not others else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
