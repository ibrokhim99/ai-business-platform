import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_a import SaturationIndexIn, SaturationIndexOut


def _sigmoid(x: float) -> float:
    """Sigmoid function mapped to [0, 1]."""
    return 1.0 / (1.0 + np.exp(-x))


# Benchmark: density considered "saturated" at 5 outlets per 10k population
_DENSITY_SATURATION_POINT = 5.0
# Benchmark: revenue per outlet considered "low" when below this (high competition effect)
_REVENUE_FLOOR = 20_000.0
_REVENUE_CEILING = 200_000.0


@register_model("M-A3")
class SaturationIndexModel(BaseMLModel[SaturationIndexIn, SaturationIndexOut]):
    metadata = ModelMetadata(
        model_id="M-A3",
        block="A",
        name="Saturation Index",
        version="1.0.0",
        algorithm="Sigmoid-normalized composite density + revenue concentration index",
        is_stub=False,
        feature_names=["competitor_count", "population", "avg_revenue_per_outlet"],
        supported_explainers=["rule_based"],
        description="Competition saturation index 0–100 using sigmoid normalization.",
    )

    def predict(self, input_data: SaturationIndexIn) -> SaturationIndexOut:
        # Density: competitors per 10k population
        density = input_data.competitor_count / max(input_data.population / 10_000, 0.1)

        # Density component: sigmoid centred at _DENSITY_SATURATION_POINT, scaled to 0-60
        # density at saturation point → 0.5 sigmoid → 30 points
        density_raw = _sigmoid((density - _DENSITY_SATURATION_POINT) * 0.8)
        density_component = float(density_raw * 60.0)

        # Revenue concentration: low revenue per outlet → high saturation (pressure on margins)
        rev_norm = np.clip(
            (input_data.avg_revenue_per_outlet - _REVENUE_FLOOR) / (_REVENUE_CEILING - _REVENUE_FLOOR),
            0.0, 1.0,
        )
        # Low revenue → high saturation contribution
        revenue_component = float((1.0 - rev_norm) * 40.0)

        idx = round(float(np.clip(density_component + revenue_component, 0, 100)), 1)

        if idx < 25:
            level = "low"
        elif idx < 50:
            level = "medium"
        elif idx < 75:
            level = "high"
        else:
            level = "critical"

        return SaturationIndexOut(
            saturation_index=idx,
            level=level,
            components={
                "density_component": round(density_component, 1),
                "revenue_component": round(revenue_component, 1),
                "density_per_10k": round(density, 3),
                "revenue_norm": round(float(rev_norm), 3),
            },
        )

    def explain(self, input_data: SaturationIndexIn) -> dict:
        density = input_data.competitor_count / max(input_data.population / 10_000, 0.1)
        density_raw = _sigmoid((density - _DENSITY_SATURATION_POINT) * 0.8)
        revenue_contribution = 0.40
        density_contribution = 0.60
        return {
            "competitor_density": round(density_contribution * density_raw * 2, 4),
            "avg_revenue_per_outlet": round(revenue_contribution, 4),
            "density_per_10k_pop": round(density, 3),
            "saturation_boundary": _DENSITY_SATURATION_POINT,
        }
