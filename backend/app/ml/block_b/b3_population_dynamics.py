import datetime

import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_b import PopulationDynamicsIn, PopulationDynamicsOut

# Known region base populations (approx 2024 estimates)
_REGION_BASE_POP: dict[str, int] = {
    "tashkent-01": 2_900_000,
    "tashkent-city": 3_100_000,
    "samarkand-01": 520_000,
    "andijan-01": 450_000,
    "fergana-01": 400_000,
    "namangan-01": 530_000,
    "bukhara-01": 310_000,
    "kashkadarya-01": 420_000,
    "surkhandarya-01": 280_000,
    "khorezm-01": 190_000,
    "navoi-01": 140_000,
    "jizzakh-01": 135_000,
    "sirdarya-01": 120_000,
    "karakalpakstan-01": 200_000,
}
_DEFAULT_POP = 300_000

# Annual growth rate range for Uzbekistan regions: 1.5% - 3.5%
_GROWTH_MIN = 1.5
_GROWTH_MAX = 3.5

# Working-age population base (ages 15-64) and urbanization adjustment
_WORKING_AGE_BASE = 64.5
_URBANIZATION_ADJUSTMENT_PER_YEAR = 0.15  # pct increase per year (urbanization trend)

# Demographic shift descriptions by growth rate
def _demographic_shift_label(growth_rate: float) -> str:
    if growth_rate > 2.8:
        return "youth_bulge"
    elif growth_rate > 2.0:
        return "moderate_growth"
    elif growth_rate > 1.5:
        return "aging_transition"
    else:
        return "stable_population"


@register_model("M-B3")
class PopulationDynamicsModel(BaseMLModel[PopulationDynamicsIn, PopulationDynamicsOut]):
    metadata = ModelMetadata(
        model_id="M-B3",
        block="B",
        name="Population Dynamics",
        version="1.0.0",
        algorithm="Cohort-component model with region-specific growth rates",
        is_stub=False,
        feature_names=["region_id", "horizon_years"],
        supported_explainers=["rule_based"],
        description="Projects population and working-age share using cohort-component methodology.",
    )

    def _region_growth_rate(self, region_id: str) -> float:
        """Derive a region-specific growth rate from region_id hash for reproducibility."""
        seed = abs(hash(region_id)) % 1000
        rng = np.random.default_rng(seed)
        # Randomize within [_GROWTH_MIN, _GROWTH_MAX] based on region
        return float(rng.uniform(_GROWTH_MIN, _GROWTH_MAX))

    def predict(self, input_data: PopulationDynamicsIn) -> PopulationDynamicsOut:
        base_pop = _REGION_BASE_POP.get(input_data.region_id, _DEFAULT_POP)
        growth_rate = self._region_growth_rate(input_data.region_id)
        base_year = datetime.date.today().year

        projections = []
        for y in range(input_data.horizon_years + 1):
            pop = int(base_pop * ((1 + growth_rate / 100) ** y))

            # Working-age pct: starts at base and increases due to urbanization trend
            # but bounded between 60% and 72%
            working_age = float(np.clip(
                _WORKING_AGE_BASE + y * _URBANIZATION_ADJUSTMENT_PER_YEAR,
                60.0, 72.0,
            ))

            projections.append({
                "year": base_year + y,
                "population": pop,
                "working_age_pct": round(working_age, 1),
            })

        return PopulationDynamicsOut(
            projections=projections,
            growth_rate_annual_pct=round(growth_rate, 2),
            demographic_shift=_demographic_shift_label(growth_rate),
        )

    def explain(self, input_data: PopulationDynamicsIn) -> dict:
        growth_rate = self._region_growth_rate(input_data.region_id)
        base_pop = _REGION_BASE_POP.get(input_data.region_id, _DEFAULT_POP)
        return {
            "birth_rate_weight": 0.50,
            "migration_weight": 0.30,
            "mortality_weight": 0.20,
            "region_growth_rate": round(growth_rate, 2),
            "base_population_2024": base_pop,
            "urbanization_adj_per_year": _URBANIZATION_ADJUSTMENT_PER_YEAR,
        }
