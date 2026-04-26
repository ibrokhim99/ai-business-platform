import numpy as np
from scipy import stats

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_a import GapAnalysisIn, GapAnalysisOut

# Verdict thresholds (gap as % of normative)
_UNDERSERVED_THRESHOLD = 15.0    # gap_pct > 15% → underserved
_OVERSATURATED_THRESHOLD = -15.0  # gap_pct < -15% → oversaturated


@register_model("M-A2")
class GapAnalysisModel(BaseMLModel[GapAnalysisIn, GapAnalysisOut]):
    metadata = ModelMetadata(
        model_id="M-A2",
        block="A",
        name="GAP Analysis",
        version="1.0.0",
        algorithm="Normative density calculation with Poisson significance test",
        is_stub=False,
        feature_names=["normative_density", "actual_count", "population"],
        supported_explainers=["rule_based"],
        description="Compares normative vs actual outlet density to identify market gaps.",
    )

    def predict(self, input_data: GapAnalysisIn) -> GapAnalysisOut:
        # Normative count = (population / 10,000) × normative_density
        pop_units = input_data.population / 10_000
        normative_count = pop_units * input_data.normative_density

        gap = normative_count - input_data.actual_count
        gap_pct = (gap / normative_count * 100) if normative_count > 0 else 0.0

        # Poisson exact test: is actual_count significantly different from Poisson(normative)?
        # Use scipy.stats.poisson for confidence  bounds
        alpha = 0.05
        if input_data.actual_count >= 0 and normative_count > 0:
            # p-value: probability of observing actual_count or fewer under H0: lambda=normative
            p_low = float(stats.poisson.cdf(input_data.actual_count, normative_count))
            # If p_low < alpha/2 → significantly underserved
            # Use p_low to refine the verdict threshold
            stat_underserved = p_low < alpha / 2
        else:
            stat_underserved = False

        if gap_pct > _UNDERSERVED_THRESHOLD or stat_underserved:
            verdict = "underserved"
        elif gap_pct < _OVERSATURATED_THRESHOLD:
            verdict = "oversaturated"
        else:
            verdict = "balanced"

        return GapAnalysisOut(
            normative_count=round(normative_count, 1),
            actual_count=input_data.actual_count,
            gap=round(gap, 1),
            gap_pct=round(gap_pct, 1),
            verdict=verdict,
        )

    def explain(self, input_data: GapAnalysisIn) -> dict:
        normative_count = (input_data.population / 10_000) * input_data.normative_density
        gap = normative_count - input_data.actual_count
        total_weight = abs(normative_count) + abs(input_data.actual_count) + 1e-9
        density_contrib = abs(normative_count) / total_weight
        actual_contrib = abs(input_data.actual_count) / total_weight
        return {
            "normative_density_weight": round(density_contrib * 0.7 + 0.3, 4),
            "population_weight": round(0.35, 4),
            "actual_count_weight": round(actual_contrib, 4),
            "computed_normative_count": round(normative_count, 1),
            "raw_gap": round(gap, 1),
        }
