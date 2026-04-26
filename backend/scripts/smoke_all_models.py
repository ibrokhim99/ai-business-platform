"""Run every registered ML model with a default profile and print pass/fail."""
from __future__ import annotations

import time
import traceback

from app.ml.registry import ModelRegistry
from app.services.profile_to_input import build, ChatProfile


def main() -> int:
    reg = ModelRegistry()
    ids = sorted(reg.all_ids())
    print(f"registry: {len(ids)} models loaded")

    # Default profile mirrors the seed used in the frontend.
    profile = ChatProfile(
        region_id="tashkent-01",
        mcc_code="5812",
        monthly_revenue_estimate=15_000,
        initial_investment=50_000,
    )

    fails: list[tuple[str, str]] = []
    t0 = time.time()
    for mid in ids:
        try:
            inp = build(mid, profile)
            out = reg.get(mid, "1.0.0").predict(inp)
            # Sanity: result must be non-None
            if out is None:
                raise ValueError("predict returned None")
            print(f"  ✓ {mid}")
        except Exception as e:
            fails.append((mid, f"{type(e).__name__}: {e}"))
            print(f"  ✗ {mid}: {type(e).__name__}: {e}")

    elapsed = time.time() - t0
    print()
    print(f"total: {len(ids)}, ok: {len(ids) - len(fails)}, fail: {len(fails)}, elapsed: {elapsed:.2f}s")
    if fails:
        print()
        print("=== failures ===")
        for mid, err in fails:
            print(f"  {mid}: {err}")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
