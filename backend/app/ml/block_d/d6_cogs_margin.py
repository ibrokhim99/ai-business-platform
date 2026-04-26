import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_d import COGSMarginIn, COGSMarginOut

# Industry benchmark margins by MCC code
# (cogs_pct, gross_margin_pct, operating_margin_pct, net_margin_pct)
_MCC_BENCHMARKS: dict[str, tuple[float, float, float, float]] = {
    "5812": (0.30, 0.70, 0.20, 0.15),   # Full-service restaurants
    "5814": (0.28, 0.72, 0.22, 0.17),   # Fast food: slightly better margins
    "5411": (0.65, 0.35, 0.12, 0.08),   # Grocery: high COGS, thin margins
    "5422": (0.68, 0.32, 0.10, 0.06),   # Meat markets
    "5912": (0.45, 0.55, 0.18, 0.12),   # Pharmacy
    "5122": (0.55, 0.45, 0.15, 0.10),   # Drug wholesale
    "7372": (0.18, 0.82, 0.28, 0.22),   # Software: very high margin
    "5045": (0.55, 0.45, 0.12, 0.08),   # Electronics
    "5065": (0.60, 0.40, 0.10, 0.06),   # Electronics wholesale
    "5940": (0.50, 0.50, 0.15, 0.10),   # Sporting goods
    "5941": (0.48, 0.52, 0.16, 0.11),   # Outdoor sporting
    "5661": (0.48, 0.52, 0.16, 0.10),   # Shoe stores
    "5611": (0.45, 0.55, 0.18, 0.12),   # Men's clothing
    "5621": (0.43, 0.57, 0.19, 0.13),   # Women's clothing
    "5699": (0.46, 0.54, 0.17, 0.11),   # Misc apparel
    "5999": (0.50, 0.50, 0.15, 0.10),   # Misc retail
    "5511": (0.72, 0.28, 0.08, 0.05),   # Auto dealers: very high COGS
    "7531": (0.35, 0.65, 0.25, 0.18),   # Auto body/service
    "7011": (0.40, 0.60, 0.22, 0.15),   # Hotels/lodging
    "7012": (0.38, 0.62, 0.24, 0.17),   # Timeshare
}
_DEFAULT_BENCHMARK = (0.45, 0.55, 0.15, 0.10)

# Region-specific cost index adjustments (cost pressures by region)
_REGION_COST_INDEX: dict[str, float] = {
    "tashkent-01": 1.05,     # Higher costs in capital
    "tashkent-city": 1.08,
    "samarkand-01": 0.96,
    "andijan-01": 0.93,
    "fergana-01": 0.94,
    "namangan-01": 0.92,
    "navoi-01": 0.98,
}
_DEFAULT_COST_INDEX = 1.0

# Revenue scale adjustment: larger revenue → slight margin improvement (economies of scale)
_SCALE_THRESHOLDS = [
    (10_000, -0.02),    # <$10k/month: penalty
    (50_000, 0.0),      # $10k-$50k: baseline
    (100_000, 0.01),    # $50k-$100k: slight improvement
    (500_000, 0.025),   # $100k-$500k: moderate improvement
]


def _scale_adjustment(monthly_revenue: float) -> float:
    """Return margin adjustment based on revenue scale."""
    adj = -0.02
    for threshold, a in _SCALE_THRESHOLDS:
        if monthly_revenue >= threshold:
            adj = a
    return adj


def _benchmark_comparison(actual_net: float, benchmark_net: float) -> str:
    """Compare actual net margin to benchmark."""
    if actual_net > benchmark_net * 1.10:
        return "above"
    elif actual_net < benchmark_net * 0.90:
        return "below"
    else:
        return "at"


@register_model("M-D6")
class COGSMarginModel(BaseMLModel[COGSMarginIn, COGSMarginOut]):
    metadata = ModelMetadata(
        model_id="M-D6",
        block="D",
        name="COGS & Margin Estimator",
        version="1.0.0",
        algorithm="MCC industry benchmarks with region cost index and revenue scale adjustments",
        is_stub=False,
        feature_names=["mcc_code", "monthly_revenue", "region_id"],
        supported_explainers=["rule_based"],
        description="COGS and margin benchmarks calibrated by MCC, region, and revenue scale.",
    )

    def predict(self, input_data: COGSMarginIn) -> COGSMarginOut:
        cogs_raw, gross_raw, operating_raw, net_raw = _MCC_BENCHMARKS.get(
            input_data.mcc_code, _DEFAULT_BENCHMARK
        )

        # Apply region cost index: higher regional costs → higher COGS
        cost_index = _REGION_COST_INDEX.get(input_data.region_id, _DEFAULT_COST_INDEX)
        cogs_adj = float(np.clip(cogs_raw * cost_index, 0.05, 0.90))

        # Recalculate gross margin from adjusted COGS
        gross_adj = 1.0 - cogs_adj

        # Scale effect on operating and net margins
        scale_adj = _scale_adjustment(input_data.monthly_revenue)
        operating_adj = float(np.clip(operating_raw + scale_adj, 0.01, gross_adj))
        net_adj = float(np.clip(net_raw + scale_adj * 0.8, 0.005, operating_adj))

        # Benchmark comparison: compare net to pure benchmark
        comparison = _benchmark_comparison(net_adj, net_raw)

        return COGSMarginOut(
            cogs_pct=round(cogs_adj * 100, 2),
            gross_margin_pct=round(gross_adj * 100, 2),
            operating_margin_pct=round(operating_adj * 100, 2),
            net_margin_pct=round(net_adj * 100, 2),
            benchmark_source="central_asia_industry_benchmarks_v1",
            industry_comparison=comparison,
        )

    def explain(self, input_data: COGSMarginIn) -> dict:
        cogs_raw, _, _, net_raw = _MCC_BENCHMARKS.get(input_data.mcc_code, _DEFAULT_BENCHMARK)
        cost_index = _REGION_COST_INDEX.get(input_data.region_id, _DEFAULT_COST_INDEX)
        scale_adj = _scale_adjustment(input_data.monthly_revenue)
        return {
            "mcc_sector_weight": 0.70,
            "scale_effect_weight": 0.20,
            "region_adjustment_weight": 0.10,
            "mcc_benchmark_cogs_pct": round(cogs_raw * 100, 1),
            "mcc_benchmark_net_pct": round(net_raw * 100, 1),
            "region_cost_index": cost_index,
            "scale_margin_adjustment": round(scale_adj, 4),
        }
