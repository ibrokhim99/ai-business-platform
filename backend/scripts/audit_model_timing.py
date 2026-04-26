"""Per-model timing audit with input variations and per-call timeouts.

Reports models that are slow (>1.5s), hang (>15s, killed), or error.
Each model is called with several profile variations to expose
input-dependent freezes that a single default profile would hide.
"""
from __future__ import annotations

import concurrent.futures
import time
import traceback
from dataclasses import dataclass

from app.ml.registry import ModelRegistry
from app.services.profile_to_input import build, ChatProfile


SLOW_THRESHOLD_S = 1.5
TIMEOUT_S = 15.0


@dataclass
class CallResult:
    model_id: str
    variant: str
    elapsed_s: float
    status: str  # ok | slow | timeout | error
    error: str = ""


VARIANTS: dict[str, ChatProfile] = {
    "default":         ChatProfile(region_id="tashkent-01", mcc_code="5812", monthly_revenue_estimate=15_000, initial_investment=50_000),
    "tiny_business":   ChatProfile(region_id="tashkent-01", mcc_code="5812", monthly_revenue_estimate=2_000,  initial_investment=8_000),
    "huge_business":   ChatProfile(region_id="tashkent-01", mcc_code="5812", monthly_revenue_estimate=500_000, initial_investment=2_000_000),
    "different_mcc":   ChatProfile(region_id="samarkand-01", mcc_code="5411", monthly_revenue_estimate=22_000, initial_investment=80_000),
    "long_horizon":    ChatProfile(region_id="tashkent-01", mcc_code="5812", monthly_revenue_estimate=15_000, initial_investment=50_000, horizon_months=120),
}


def _run_single(reg: ModelRegistry, mid: str, profile: ChatProfile) -> tuple[float, str]:
    inp = build(mid, profile)
    out = reg.get(mid, "1.0.0").predict(inp)
    if out is None:
        raise ValueError("predict returned None")
    return 0.0, "ok"


def call_with_timeout(reg: ModelRegistry, mid: str, variant: str, profile: ChatProfile) -> CallResult:
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(_run_single, reg, mid, profile)
        try:
            fut.result(timeout=TIMEOUT_S)
            elapsed = time.time() - t0
            status = "slow" if elapsed > SLOW_THRESHOLD_S else "ok"
            return CallResult(mid, variant, elapsed, status)
        except concurrent.futures.TimeoutError:
            return CallResult(mid, variant, TIMEOUT_S, "timeout", "killed by audit timeout")
        except Exception as e:
            elapsed = time.time() - t0
            return CallResult(mid, variant, elapsed, "error", f"{type(e).__name__}: {e}"[:200])


def main() -> int:
    reg = ModelRegistry()
    ids = sorted(reg.all_ids())
    print(f"audit: {len(ids)} models x {len(VARIANTS)} variants = {len(ids) * len(VARIANTS)} calls")
    print(f"thresholds: slow>{SLOW_THRESHOLD_S}s, timeout={TIMEOUT_S}s")
    print()

    all_results: list[CallResult] = []
    t0_total = time.time()
    for mid in ids:
        results_for_mid: list[CallResult] = []
        for variant, profile in VARIANTS.items():
            r = call_with_timeout(reg, mid, variant, profile)
            results_for_mid.append(r)
            all_results.append(r)
        max_t = max(r.elapsed_s for r in results_for_mid)
        bad = [r for r in results_for_mid if r.status in ("slow", "timeout", "error")]
        marker = "✓" if not bad else ("⚠" if all(b.status == "slow" for b in bad) else "✗")
        worst = max(results_for_mid, key=lambda r: r.elapsed_s)
        print(f"  {marker} {mid:6s} max={max_t:5.2f}s  worst={worst.variant:15s} {worst.status:7s}", end="")
        if bad:
            print(f"  bad: {','.join(b.variant for b in bad)}", end="")
        print()

    elapsed_total = time.time() - t0_total
    print()
    print("=" * 80)
    slow = [r for r in all_results if r.status == "slow"]
    timeouts = [r for r in all_results if r.status == "timeout"]
    errors = [r for r in all_results if r.status == "error"]

    print(f"summary: {len(all_results)} calls in {elapsed_total:.1f}s")
    print(f"  ok:       {len(all_results) - len(slow) - len(timeouts) - len(errors)}")
    print(f"  slow (>{SLOW_THRESHOLD_S}s): {len(slow)}")
    print(f"  timeouts: {len(timeouts)}")
    print(f"  errors:   {len(errors)}")

    if slow:
        print("\n=== SLOW (>1.5s) ===")
        for r in sorted(slow, key=lambda x: -x.elapsed_s):
            print(f"  {r.model_id:6s} {r.variant:15s} {r.elapsed_s:5.2f}s")

    if timeouts:
        print("\n=== TIMEOUTS (killed at 15s) ===")
        for r in timeouts:
            print(f"  {r.model_id:6s} {r.variant}")

    if errors:
        print("\n=== ERRORS ===")
        for r in errors:
            print(f"  {r.model_id:6s} {r.variant:15s} {r.error}")

    return 0 if not (timeouts or errors) else 1


if __name__ == "__main__":
    raise SystemExit(main())
