"""
block_data — unified loader for all 10 block CSVs (data/test/block_a..j.csv).

Each model block has a corresponding 1000-row dataset. This service exposes
one entry point — `lookup_block(block, region_id, mcc_code, ...)` — that
filters the block's rows to those matching the user's profile and returns:

  - matched_count / total_examined  (so callers know how broad the match was)
  - stats:        per-column means for the matched subset
  - sample_rows:  up to N matched rows, ready to ship to the UI

The same service is used by:
  - evidence_service (frontend audit trail)
  - llm_chat_service (per-block context injected into the synthesis prompt
    so the LLM answers with real numbers, not just model output)

Datasets are loaded once on first use via lru_cache, so this is safe to call
from any request hot path.
"""
from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

# Block letter → which CSV columns to summarise in `stats` (the rest still ship
# in `sample_rows`, but stats focus on the most-relevant signals per block).
_KEY_NUMERIC_COLS: dict[str, list[str]] = {
    "A": ["population", "avg_income", "competitor_count", "avg_revenue_per_outlet", "growth_rate_pct"],
    "B": ["base_monthly_revenue", "current_avg_income", "horizon_months"],
    "C": ["radius_m", "walk_minutes"],
    "D": ["monthly_revenue_estimate", "monthly_revenue", "monthly_fixed_costs", "initial_investment",
          "monthly_rent", "gross_margin_pct", "monthly_net_cash_flow", "growth_rate_monthly_pct"],
    "E": ["monthly_revenue", "initial_investment", "owner_experience_years", "location_score",
          "competition_count", "business_age_months", "target_price", "competitor_avg_price"],
    "F": ["monthly_revenue", "monthly_revenue_estimate", "requested_loan_amount", "proposed_loan_amount",
          "owner_credit_history_score", "collateral_value", "monthly_net_cashflow",
          "current_dti", "credit_score", "revenue_trend_3m_pct"],
    "G": ["radius_m"],
    "H": ["monthly_budget", "historical_cac", "competition_intensity", "arpu_monthly",
          "gross_margin_pct", "monthly_churn_rate", "elasticity_estimate", "current_price"],
    "I": ["annual_demand", "unit_cost", "lead_time_days", "service_level", "on_hand_units",
          "daily_demand_mean", "on_time_delivery_rate", "quality_defect_rate"],
    "J": ["amount", "txn_count_last_24h", "avg_amount_last_30d", "avg_ticket_size",
          "chargeback_rate_30d", "credit_inquiries_last_6m", "device_seen_count_30d"],
}


def _find_data_dir() -> Path:
    """Mirror evidence_service._find_data_dir — same lookup, same fallback."""
    candidates = [
        Path("/data/test"),
        Path(__file__).resolve().parents[3] / "data" / "test",
        Path("/app/data/test"),
    ]
    for c in candidates:
        if c.is_dir() and (c / "block_a.csv").exists():
            return c
    return candidates[0]


_DATA_DIR = _find_data_dir()


@dataclass(frozen=True)
class BlockLookup:
    block: str
    matched_count: int
    total_examined: int
    stats: dict[str, float]
    sample_rows: list[dict[str, Any]]
    columns: list[str] = field(default_factory=list)
    source: str = ""


def _coerce(s: str | None) -> Any:
    """Best-effort: numbers as float, true/false as bool, else str."""
    if s is None or s == "":
        return None
    sl = s.strip().lower()
    if sl in ("true", "false"):
        return sl == "true"
    try:
        # int first to avoid 5.0 for integer columns
        if "." not in s and "e" not in sl and "E" not in s:
            return int(s)
        return float(s)
    except (ValueError, TypeError):
        return s


def _to_float(v: Any) -> float | None:
    try:
        if isinstance(v, bool):
            return float(v)
        if v is None or v == "":
            return None
        return float(v)
    except (ValueError, TypeError):
        return None


@lru_cache(maxsize=10)
def _load_block(letter: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Load one CSV. Cached per-block — first read pays the IO cost."""
    path = _DATA_DIR / f"block_{letter}.csv"
    if not path.exists():
        return [], []
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = list(reader.fieldnames or [])
        for raw in reader:
            rows.append({k: _coerce(v) for k, v in raw.items()})
    return cols, rows


def _filter_rows(rows: list[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Apply every (col, value) constraint where the column exists."""
    if not rows:
        return []
    cols = set(rows[0].keys())
    out = rows
    for col, val in filters.items():
        if val is None or col not in cols:
            continue
        # Coerce filter to string for comparison since CSV values are heterogeneous.
        target = str(val)
        out = [r for r in out if str(r.get(col)) == target]
    return out


def _summary_stats(rows: list[dict[str, Any]], key_cols: list[str]) -> dict[str, float]:
    """Mean per key numeric column, only on rows with a parseable value."""
    out: dict[str, float] = {}
    for col in key_cols:
        nums = [v for r in rows if (v := _to_float(r.get(col))) is not None]
        if nums:
            try:
                out[col] = round(statistics.mean(nums), 4)
            except statistics.StatisticsError:
                continue
    return out


def lookup_block(
    block: str,
    *,
    region_id: str | None = None,
    mcc_code: str | None = None,
    limit: int = 5,
) -> BlockLookup:
    """Return the matched rows + stats from one block CSV for a profile.

    Filtering strategy: AND on (region_id, mcc_code) where those columns
    exist; if that yields nothing, fall back to MCC-only; if still empty,
    return a small slice of the block as generic context.
    """
    letter = block.upper()[:1]
    cols, rows = _load_block(letter.lower())
    total = len(rows)
    if not rows:
        return BlockLookup(letter, 0, 0, {}, [], cols, source=f"block_{letter.lower()}.csv")

    # Try strict (region + MCC), then loosen.
    strict = _filter_rows(rows, {"region_id": region_id, "mcc_code": mcc_code})
    matched = strict
    if not matched and (region_id or mcc_code):
        matched = _filter_rows(rows, {"mcc_code": mcc_code})
    if not matched and (region_id or mcc_code):
        matched = _filter_rows(rows, {"region_id": region_id})
    if not matched:
        # Generic context — first N rows, sorted by row order.
        matched = rows[:50]

    key_cols = _KEY_NUMERIC_COLS.get(letter, [c for c in cols if c not in ("region_id", "mcc_code")][:6])
    stats = _summary_stats(matched, key_cols)

    sample = matched[:limit]
    return BlockLookup(
        block=letter,
        matched_count=len(matched),
        total_examined=total,
        stats=stats,
        sample_rows=sample,
        columns=cols,
        source=f"block_{letter.lower()}.csv",
    )


def lookup_blocks_for_models(
    model_ids: Iterable[str],
    *,
    region_id: str | None = None,
    mcc_code: str | None = None,
    limit: int = 5,
) -> dict[str, BlockLookup]:
    """For the unique blocks named in `model_ids` (e.g. ['M-A1','M-D5']),
    return one BlockLookup each. Used by LlmChatService to build the
    synthesis-time data context. """
    blocks: set[str] = set()
    for mid in model_ids:
        if "-" in mid and len(mid) >= 3:
            blocks.add(mid.split("-", 1)[1][:1].upper())
    return {
        b: lookup_block(b, region_id=region_id, mcc_code=mcc_code, limit=limit)
        for b in sorted(blocks)
    }
