"""
EvidenceService — surfaces the synthetic dataset rows that back a prediction.

Loads `data/test/block_a.csv` and `data/test/block_d.csv` once on first use,
joins them on (region_id, mcc_code), classifies each row as
succeeded / struggling / failed using cash-flow + growth signals, and ranks
candidates by similarity to a query profile.

This is what makes the chat reply auditable: the user can see the actual
synthetic businesses whose outcomes informed the recommendation.
"""
from __future__ import annotations

import csv
import math
import statistics
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable

# Find data/test wherever it lives — prefers Docker volume mount, falls back
# to the repo-root layout used during local development.
def _find_data_dir() -> Path:
    candidates = [
        Path("/data/test"),                                       # docker-compose volume mount
        Path(__file__).resolve().parents[3] / "data" / "test",    # repo root (local dev)
        Path("/app/data/test"),                                   # data baked into the image
    ]
    for c in candidates:
        if c.is_dir() and (c / "block_a.csv").exists():
            return c
    return candidates[0]  # surfaces "missing" cleanly via empty CSV reads


_DATA_DIR = _find_data_dir()

_NICHE_LABELS = {
    "restaurant":        "Restoran",
    "fast_food":         "Tez ovqatlanish",
    "grocery":           "Oziq-ovqat",
    "pharmacy":          "Dorixona",
    "clothing":          "Kiyim",
    "womens_clothing":   "Ayollar kiyimi",
    "furniture":         "Mebel",
    "hotel":             "Mehmonxona",
    "electronics":       "Elektronika",
    "auto_dealer":       "Avtomobil savdosi",
    "medical_equipment": "Tibbiyot jihozlari",
    "software":          "Dasturiy taʻminot",
    "sports":            "Sport",
    "retail":            "Chakana savdo",
}


@dataclass(frozen=True)
class _MarketRow:
    region_id: str
    mcc_code: str
    niche: str
    avg_revenue_per_outlet: float
    growth_rate_pct: float
    competitor_count: int


@dataclass(frozen=True)
class _FinancialRow:
    region_id: str
    mcc_code: str
    monthly_revenue: float
    initial_investment: float
    monthly_net_cash_flow: float
    gross_margin_pct: float


def _safe_float(s: str | None, default: float = 0.0) -> float:
    try:
        return float(s) if s not in (None, "") else default
    except ValueError:
        return default


def _safe_int(s: str | None, default: int = 0) -> int:
    try:
        return int(float(s)) if s not in (None, "") else default
    except ValueError:
        return default


@lru_cache(maxsize=1)
def _load_market() -> list[_MarketRow]:
    path = _DATA_DIR / "block_a.csv"
    if not path.exists():
        return []
    out: list[_MarketRow] = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(_MarketRow(
                region_id=r["region_id"],
                mcc_code=r["mcc_code"],
                niche=r.get("niche", ""),
                avg_revenue_per_outlet=_safe_float(r.get("avg_revenue_per_outlet")),
                growth_rate_pct=_safe_float(r.get("growth_rate_pct")),
                competitor_count=_safe_int(r.get("competitor_count")),
            ))
    return out


@lru_cache(maxsize=1)
def _load_financial() -> list[_FinancialRow]:
    path = _DATA_DIR / "block_d.csv"
    if not path.exists():
        return []
    out: list[_FinancialRow] = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(_FinancialRow(
                region_id=r["region_id"],
                mcc_code=r["mcc_code"],
                monthly_revenue=_safe_float(r.get("monthly_revenue") or r.get("monthly_revenue_estimate")),
                initial_investment=_safe_float(r.get("initial_investment")),
                monthly_net_cash_flow=_safe_float(r.get("monthly_net_cash_flow")),
                gross_margin_pct=_safe_float(r.get("gross_margin_pct")),
            ))
    return out


def _outcome(growth: float, net_cash_flow: float) -> str:
    """Classify a synthetic business based on cash-flow and growth.

    Cash flow is the dominant signal: a business losing money each month is
    failing regardless of how the local market is growing. Growth breaks the
    tie when cash flow is roughly flat.
    """
    if net_cash_flow is None or net_cash_flow == 0:
        # Fall back to growth alone when financial row is missing
        if growth > 5: return "succeeded"
        if growth < -2: return "failed"
        return "struggling"
    if net_cash_flow >= 0 and growth >= 0: return "succeeded"
    if net_cash_flow < 0 and growth < 0: return "failed"
    return "struggling"


def _similarity(
    query_revenue: float | None,
    query_investment: float | None,
    candidate_revenue: float,
    candidate_investment: float,
    region_match: bool,
    mcc_match: bool,
) -> float:
    """0..1 similarity score. Region/MCC matches dominate; revenue/capital refine."""
    score = 0.0
    if region_match: score += 0.45
    if mcc_match:    score += 0.45

    def _close(a: float | None, b: float) -> float:
        if not a or a <= 0 or b <= 0: return 0.0
        ratio = min(a, b) / max(a, b)
        return ratio  # 1.0 when identical, lower as they diverge

    rev_close = _close(query_revenue, candidate_revenue) if query_revenue else 0.0
    inv_close = _close(query_investment, candidate_investment) if query_investment else 0.0
    # Each contributes up to 0.05 — never enough to overcome a region/MCC mismatch
    score += 0.05 * rev_close + 0.05 * inv_close
    return min(1.0, score)


@dataclass(frozen=True)
class EvidenceRow:
    region_id: str
    mcc_code: str
    niche: str
    niche_label: str
    monthly_revenue: float
    initial_investment: float
    monthly_net_cash_flow: float
    growth_rate_pct: float
    competitor_count: int
    gross_margin_pct: float
    outcome: str
    similarity: float


@dataclass(frozen=True)
class EvidenceSummary:
    succeeded: int
    struggling: int
    failed: int
    median_revenue: float
    median_growth_pct: float


@dataclass(frozen=True)
class BlockEvidence:
    """Per-block snapshot of the rows that informed a specific model's output."""
    block: str
    matched_count: int
    total_examined: int
    stats: dict[str, float]
    sample_rows: list[dict]
    source: str


@dataclass(frozen=True)
class EvidenceResult:
    rows: list[EvidenceRow]
    summary: EvidenceSummary
    total_examined: int
    sources: list[str]
    blocks: list[BlockEvidence] = field(default_factory=list)


class EvidenceService:
    """Builds an audit trail of the synthetic data behind a prediction.

    Stateless aside from the lru_cached CSV loaders.
    """

    def find_similar(
        self,
        *,
        region_id: str | None,
        mcc_code: str | None,
        monthly_revenue: float | None = None,
        initial_investment: float | None = None,
        limit: int = 10,
        blocks: list[str] | None = None,
    ) -> EvidenceResult:
        market = _load_market()
        financial = _load_financial()
        if not market:
            return EvidenceResult(
                rows=[], summary=EvidenceSummary(0, 0, 0, 0.0, 0.0),
                total_examined=0, sources=[],
            )

        # Index financial rows by (region, mcc) so we can attach cash-flow data.
        # Multiple rows per key are possible in synthetic data — average them.
        fin_index: dict[tuple[str, str], list[_FinancialRow]] = {}
        for f in financial:
            fin_index.setdefault((f.region_id, f.mcc_code), []).append(f)

        candidates: list[tuple[float, EvidenceRow]] = []
        for m in market:
            fin_rows = fin_index.get((m.region_id, m.mcc_code), [])
            if fin_rows:
                cand_rev = statistics.mean(r.monthly_revenue for r in fin_rows)
                cand_inv = statistics.mean(r.initial_investment for r in fin_rows)
                cand_ncf = statistics.mean(r.monthly_net_cash_flow for r in fin_rows)
                cand_margin = statistics.mean(r.gross_margin_pct for r in fin_rows)
            else:
                cand_rev = m.avg_revenue_per_outlet
                cand_inv = 0.0
                cand_ncf = 0.0
                cand_margin = 0.0

            sim = _similarity(
                query_revenue=monthly_revenue,
                query_investment=initial_investment,
                candidate_revenue=cand_rev,
                candidate_investment=cand_inv,
                region_match=bool(region_id) and m.region_id == region_id,
                mcc_match=bool(mcc_code) and m.mcc_code == mcc_code,
            )

            row = EvidenceRow(
                region_id=m.region_id,
                mcc_code=m.mcc_code,
                niche=m.niche,
                niche_label=_NICHE_LABELS.get(m.niche, m.niche.title() or "—"),
                monthly_revenue=round(cand_rev, 2),
                initial_investment=round(cand_inv, 2),
                monthly_net_cash_flow=round(cand_ncf, 2),
                growth_rate_pct=round(m.growth_rate_pct, 2),
                competitor_count=m.competitor_count,
                gross_margin_pct=round(cand_margin, 2),
                outcome=_outcome(m.growth_rate_pct, cand_ncf),
                similarity=round(sim, 3),
            )
            candidates.append((sim, row))

        candidates.sort(key=lambda x: x[0], reverse=True)
        all_rows = [r for _, r in candidates]
        # Show variety: collapse to one row per (region, mcc) for the top list
        seen: set[tuple[str, str]] = set()
        top: list[EvidenceRow] = []
        for _, r in candidates:
            key = (r.region_id, r.mcc_code)
            if key in seen: continue
            seen.add(key)
            top.append(r)
            if len(top) >= limit: break

        summary = EvidenceSummary(
            succeeded=sum(1 for r in all_rows if r.outcome == "succeeded"),
            struggling=sum(1 for r in all_rows if r.outcome == "struggling"),
            failed=sum(1 for r in all_rows if r.outcome == "failed"),
            median_revenue=round(statistics.median(r.monthly_revenue for r in all_rows), 2) if all_rows else 0.0,
            median_growth_pct=round(statistics.median(r.growth_rate_pct for r in all_rows), 2) if all_rows else 0.0,
        )

        # Per-block evidence — pull a few matched rows + stats from each block
        # the caller is interested in (default: all 10). This is the data the
        # frontend uses to show "Bu javob qaysi maʻlumotlarga asoslangan?".
        from app.services.block_data import lookup_block as _lookup_block
        target_blocks = blocks if blocks else list("ABCDEFGHIJ")
        block_evidence: list[BlockEvidence] = []
        all_sources: list[str] = ["data/test/block_a.csv", "data/test/block_d.csv"]
        for b in target_blocks:
            bl = _lookup_block(b, region_id=region_id, mcc_code=mcc_code, limit=5)
            if bl.total_examined == 0:
                continue
            block_evidence.append(BlockEvidence(
                block=bl.block,
                matched_count=bl.matched_count,
                total_examined=bl.total_examined,
                stats=bl.stats,
                sample_rows=bl.sample_rows,
                source=bl.source,
            ))
            src = f"data/test/{bl.source}"
            if src not in all_sources:
                all_sources.append(src)

        return EvidenceResult(
            rows=top,
            summary=summary,
            total_examined=len(all_rows),
            sources=all_sources,
            blocks=block_evidence,
        )


_singleton: EvidenceService | None = None


def get_evidence_service() -> EvidenceService:
    global _singleton
    if _singleton is None:
        _singleton = EvidenceService()
    return _singleton
