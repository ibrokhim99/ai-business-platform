"""
EvidenceService — surfaces the synthetic dataset rows that back a prediction.

Loads `data/test/block_a.csv` and `data/test/block_d.csv` once on first use,
joins them on (region_id, mcc_code), classifies each row as
succeeded / struggling / failed using cash-flow + growth signals, ranks
candidates by similarity to a query profile, and surfaces same-area
alternative businesses when the requested one looks weak.

This is what makes the chat reply auditable: the user can see the actual
synthetic businesses whose outcomes informed the recommendation.
"""
from __future__ import annotations

import csv
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
class AlternativeBusiness:
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
    success_rate: float
    support_count: int
    rationale: str


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
    alternatives: list[AlternativeBusiness] = field(default_factory=list)


def _mean(values: Iterable[float | int]) -> float:
    seq = list(values)
    return statistics.mean(seq) if seq else 0.0


def _positive_ratio(value: float, ceiling: float) -> float:
    if value <= 0 or ceiling <= 0:
        return 0.0
    return min(value / ceiling, 1.0)


def _inverse_ratio(value: float, ceiling: float) -> float:
    if ceiling <= 0:
        return 1.0
    return max(0.0, 1.0 - min(value / ceiling, 1.0))


def _build_rationale(success_rate: float, growth_rate_pct: float, monthly_net_cash_flow: float) -> str:
    return (
        f"{round(success_rate * 100)}% o'xshash holat muvaffaqiyatli, "
        f"o'rtacha o'sish {growth_rate_pct:.1f}%, "
        f"oylik sof pul oqimi {monthly_net_cash_flow:,.0f}."
    )


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

        def _matches_requested_scope(row: EvidenceRow) -> bool:
            if region_id and row.region_id != region_id:
                return False
            if mcc_code and row.mcc_code != mcc_code:
                return False
            return True

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
        if region_id or mcc_code:
            matched_candidates = [(sim, row) for sim, row in candidates if _matches_requested_scope(row)]
        else:
            matched_candidates = candidates
        matched_rows = [row for _, row in matched_candidates]
        top = matched_rows[:limit]

        summary = EvidenceSummary(
            succeeded=sum(1 for r in matched_rows if r.outcome == "succeeded"),
            struggling=sum(1 for r in matched_rows if r.outcome == "struggling"),
            failed=sum(1 for r in matched_rows if r.outcome == "failed"),
            median_revenue=round(statistics.median(r.monthly_revenue for r in matched_rows), 2) if matched_rows else 0.0,
            median_growth_pct=round(statistics.median(r.growth_rate_pct for r in matched_rows), 2) if matched_rows else 0.0,
        )
        alternatives = self._find_alternatives(
            candidates=[row for _, row in candidates],
            region_id=region_id,
            exclude_mcc_code=mcc_code,
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
            total_examined=len(matched_rows),
            sources=all_sources,
            blocks=block_evidence,
            alternatives=alternatives,
        )

    def _find_alternatives(
        self,
        *,
        candidates: list[EvidenceRow],
        region_id: str | None,
        exclude_mcc_code: str | None,
        limit: int = 3,
    ) -> list[AlternativeBusiness]:
        """Rank same-region business categories that historically look healthier.

        We aggregate dataset rows per (region, MCC), keep only the same region as
        the user's requested area, and score alternatives by a blend of:
        success rate, growth, positive net cash flow, and lower competition.
        """
        if not region_id:
            return []

        grouped: dict[tuple[str, str, str, str], list[EvidenceRow]] = {}
        for row in candidates:
            if row.region_id != region_id:
                continue
            if exclude_mcc_code and row.mcc_code == exclude_mcc_code:
                continue
            grouped.setdefault((row.region_id, row.mcc_code, row.niche, row.niche_label), []).append(row)

        if not grouped:
            return []

        stats_by_group: list[dict[str, float | int | str]] = []
        for (cand_region, cand_mcc, cand_niche, cand_label), rows in grouped.items():
            success_rate = sum(1 for row in rows if row.outcome == "succeeded") / len(rows)
            avg_revenue = _mean(row.monthly_revenue for row in rows)
            avg_investment = _mean(row.initial_investment for row in rows)
            avg_cashflow = _mean(row.monthly_net_cash_flow for row in rows)
            avg_growth = _mean(row.growth_rate_pct for row in rows)
            avg_competition = _mean(row.competitor_count for row in rows)
            avg_margin = _mean(row.gross_margin_pct for row in rows)
            stats_by_group.append({
                "region_id": cand_region,
                "mcc_code": cand_mcc,
                "niche": cand_niche,
                "niche_label": cand_label,
                "monthly_revenue": avg_revenue,
                "initial_investment": avg_investment,
                "monthly_net_cash_flow": avg_cashflow,
                "growth_rate_pct": avg_growth,
                "competitor_count": avg_competition,
                "gross_margin_pct": avg_margin,
                "success_rate": success_rate,
                "support_count": len(rows),
            })

        max_growth = max((max(float(s["growth_rate_pct"]), 0.0) for s in stats_by_group), default=0.0)
        max_cashflow = max((max(float(s["monthly_net_cash_flow"]), 0.0) for s in stats_by_group), default=0.0)
        max_competition = max((float(s["competitor_count"]) for s in stats_by_group), default=0.0)

        ranked: list[tuple[float, float, float, AlternativeBusiness]] = []
        for stat in stats_by_group:
            success_rate = float(stat["success_rate"])
            growth_rate_pct = float(stat["growth_rate_pct"])
            monthly_net_cash_flow = float(stat["monthly_net_cash_flow"])
            competitor_count = float(stat["competitor_count"])

            qualifies = success_rate >= 0.55 or (
                success_rate >= 0.45 and monthly_net_cash_flow > 0 and growth_rate_pct > 0
            )
            if not qualifies:
                continue

            score = (
                0.55 * success_rate
                + 0.20 * _positive_ratio(growth_rate_pct, max_growth)
                + 0.20 * _positive_ratio(monthly_net_cash_flow, max_cashflow)
                + 0.05 * _inverse_ratio(competitor_count, max_competition)
            )
            ranked.append((
                score,
                success_rate,
                monthly_net_cash_flow,
                AlternativeBusiness(
                    region_id=str(stat["region_id"]),
                    mcc_code=str(stat["mcc_code"]),
                    niche=str(stat["niche"]),
                    niche_label=str(stat["niche_label"]),
                    monthly_revenue=round(float(stat["monthly_revenue"]), 2),
                    initial_investment=round(float(stat["initial_investment"]), 2),
                    monthly_net_cash_flow=round(monthly_net_cash_flow, 2),
                    growth_rate_pct=round(growth_rate_pct, 2),
                    competitor_count=int(round(competitor_count)),
                    gross_margin_pct=round(float(stat["gross_margin_pct"]), 2),
                    success_rate=round(success_rate, 3),
                    support_count=int(stat["support_count"]),
                    rationale=_build_rationale(success_rate, growth_rate_pct, monthly_net_cash_flow),
                ),
            ))

        ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return [alt for _, _, _, alt in ranked[:limit]]


_singleton: EvidenceService | None = None


def get_evidence_service() -> EvidenceService:
    global _singleton
    if _singleton is None:
        _singleton = EvidenceService()
    return _singleton
