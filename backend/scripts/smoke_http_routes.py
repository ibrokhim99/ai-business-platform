"""Hit one HTTP route per block via the running FastAPI app to prove auth + routing."""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error

from app.ml.registry import ModelRegistry
from app.services.profile_to_input import build, ChatProfile

BASE = "http://localhost:8000/api/v1"
EMAIL = "admin@bank.uz"
PASSWORD = "admin123"

# Pull endpoint paths from the frontend models.ts equivalents (one per block).
ENDPOINTS = {
    "M-A1": "/market-analysis/market-sizing",
    "M-B1": "/forecasting/revenue-forecast" if False else None,  # discover at runtime
}


def post(path: str, body: dict, token: str | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}") if e.fp else {}


def discover_endpoints() -> dict[str, str]:
    """Map each model_id to its HTTP route by scraping the OpenAPI spec."""
    with urllib.request.urlopen("http://localhost:8000/openapi.json") as r:
        spec = json.loads(r.read().decode())
    out: dict[str, str] = {}
    # Each route's operationId roughly maps to its endpoint path; we walk paths
    # and infer model id from the path's last segment + block prefix.
    block_prefixes = {
        "market-analysis": "A", "forecasting": "B", "location": "C",
        "financial": "D", "competition": "E", "credit": "F",
        "social": "G", "marketing": "H", "operations": "I", "fraud": "J",
    }
    # Walk model registry to find each model's endpoint via metadata if present;
    # fall back to listing first POST per block.
    routes_by_block: dict[str, list[str]] = {b: [] for b in block_prefixes.values()}
    for path, methods in spec.get("paths", {}).items():
        if "post" not in methods:
            continue
        for prefix, block in block_prefixes.items():
            if path.startswith(f"/api/v1/{prefix}/"):
                routes_by_block[block].append(path.replace("/api/v1", ""))
                break
    return routes_by_block


def main() -> int:
    # Login
    status, tok = post("/auth/token", {"email": EMAIL, "password": PASSWORD})
    if status != 200:
        print(f"login failed: {status} {tok}")
        return 1
    token = tok["access_token"]
    print(f"login ok, token len={len(token)}")

    routes_by_block = discover_endpoints()
    reg = ModelRegistry()
    profile = ChatProfile(
        region_id="tashkent-01",
        mcc_code="5812",
        monthly_revenue_estimate=15_000,
        initial_investment=50_000,
    )

    # For each block, build the input for the first model, but call HTTP route 0.
    # The endpoint and input must match — easier path: map model_id → endpoint via
    # the registry's metadata if available. We simply use first model per block
    # and its first route, accepting that the test is a sample.
    samples = {
        "A": ("M-A1", "/market-analysis/market-sizing"),
        "B": ("M-B1", "/forecasting/revenue-forecast"),
        "C": ("M-C1", "/location/location-fit"),
        "D": ("M-D1", "/financial/break-even"),
        "E": ("M-E1", "/competition/competition-density"),
        "F": ("M-F1", "/credit/credit-default-pd"),
        "G": ("M-G1", "/social/customer-segmentation"),
        "H": ("M-H1", "/marketing/cac-predictor"),
        "I": ("M-I1", "/operations/inventory-eoq"),
        "J": ("M-J1", "/fraud/transaction-anomaly"),
    }

    # Override with actually-existing routes per block by introspecting the spec.
    for block, routes in routes_by_block.items():
        if routes:
            mid = f"M-{block}1"
            samples[block] = (mid, routes[0])

    fails = []
    t0 = time.time()
    for block, (mid, route) in sorted(samples.items()):
        try:
            inp_obj = build(mid, profile)
            inp_dict = inp_obj.model_dump() if hasattr(inp_obj, "model_dump") else dict(inp_obj)
        except Exception as e:
            print(f"  ✗ {block} {mid} → {route}: build error: {e}")
            fails.append(mid)
            continue
        try:
            status, body = post(route, inp_dict, token=token)
            ok = status == 200
            mark = "✓" if ok else "✗"
            preview = json.dumps(body)[:100]
            print(f"  {mark} {block} {mid:6s} POST {route:42s} HTTP {status}  {preview}")
            if not ok:
                fails.append(mid)
        except Exception as e:
            print(f"  ✗ {block} {mid:6s} POST {route}: {e}")
            fails.append(mid)

    elapsed = time.time() - t0
    print()
    print(f"http: {len(samples)} blocks, ok: {len(samples) - len(fails)}, fail: {len(fails)}, elapsed: {elapsed:.2f}s")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
