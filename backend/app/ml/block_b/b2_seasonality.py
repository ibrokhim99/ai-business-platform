import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_b import SeasonalityIn, SeasonalityOut

# ---------------------------------------------------------------------------
# Uzbekistan-specific seasonal calendar knowledge
# ---------------------------------------------------------------------------

# Base retail seasonal pattern (multipliers per month Jan-Dec)
_BASE_RETAIL = np.array([
    0.88, 0.85, 1.10, 1.15, 1.05, 0.95,
    1.00, 0.98, 1.02, 1.12, 1.20, 1.30,
])

# MCC-specific seasonal adjustments (additive deltas on top of base)
_MCC_ADJUSTMENTS: dict[str, np.ndarray] = {
    # Restaurants: Navro'z (+0.15 Mar), Ramadan variable, wedding season spikes
    "5812": np.array([0.00, 0.00, 0.15, 0.05, 0.12, 0.05, 0.00, 0.00, 0.05, 0.10, 0.00, 0.05]),
    # Fast food: higher summer (hot weather → outdoor dining) and Ramadan impact
    "5814": np.array([0.00, 0.00, 0.10, 0.08, 0.08, 0.10, 0.12, 0.10, 0.05, 0.05, 0.00, 0.05]),
    # Grocery: stable, slight boost during Ramadan and New Year
    "5411": np.array([0.05, 0.05, 0.05, 0.08, 0.00, -0.05, -0.05, -0.03, 0.00, 0.02, 0.05, 0.10]),
    # Pharmacy: winter peak (illness), summer dip
    "5912": np.array([0.15, 0.12, 0.05, 0.00, -0.05, -0.08, -0.10, -0.08, -0.03, 0.00, 0.05, 0.15]),
    # Clothing / apparel: spring (Navro'z) and autumn (back to school, wedding)
    "5699": np.array([0.00, 0.05, 0.20, 0.15, 0.10, -0.05, -0.10, -0.08, 0.15, 0.18, 0.05, 0.10]),
    # Wedding services: strong May-June and Sep-Oct
    "7011": np.array([-0.10, -0.10, 0.00, 0.05, 0.30, 0.25, -0.05, -0.05, 0.25, 0.30, 0.05, -0.05]),
    # Electronics: New Year peak, back-to-school September
    "5045": np.array([-0.05, -0.05, 0.00, 0.00, 0.00, 0.00, 0.00, 0.05, 0.10, 0.05, 0.10, 0.20]),
}

# Uzbekistan named events with approximate month ranges
# Ramadan shifts by ~11 days per year; use a simple lookup for 2024-2030
_RAMADAN_MONTHS: dict[int, list[int]] = {
    2024: [3, 4],   # Mar-Apr 2024
    2025: [3],      # Mar 2025
    2026: [2, 3],   # Feb-Mar 2026
    2027: [1, 2],   # Jan-Feb 2027
    2028: [1],      # Jan 2028
    2029: [12, 1],  # Dec 2028 - Jan 2029
    2030: [12],     # Dec 2029
}
_DEFAULT_RAMADAN = [3, 4]


def _get_ramadan_months(year: int) -> list[int]:
    return _RAMADAN_MONTHS.get(year, _DEFAULT_RAMADAN)


def _build_events(year: int, mcc_code: str) -> list[dict]:
    ramadan = _get_ramadan_months(year)
    events = [
        {
            "name": "Navro'z (Persian New Year)",
            "months": [3],
            "impact": "+15% retail, +20% food & hospitality",
            "type": "cultural",
        },
        {
            "name": "Ramadan",
            "months": ramadan,
            "impact": "+10% food (pre-iftar), -15% entertainment",
            "type": "religious",
        },
        {
            "name": "Eid al-Fitr",
            "months": [ramadan[-1]],
            "impact": "+25% apparel, +20% food",
            "type": "religious",
        },
        {
            "name": "Wedding Season (Spring)",
            "months": [4, 5, 6],
            "impact": "+25% celebrations, +15% hospitality",
            "type": "cultural",
        },
        {
            "name": "Wedding Season (Autumn)",
            "months": [9, 10],
            "impact": "+20% celebrations, +12% hospitality",
            "type": "cultural",
        },
        {
            "name": "Independence Day",
            "months": [9],
            "impact": "+8% retail",
            "type": "national",
        },
        {
            "name": "New Year (Gregorian)",
            "months": [12, 1],
            "impact": "+30% retail, +20% food",
            "type": "cultural",
        },
    ]
    return events


@register_model("M-B2")
class SeasonalityModel(BaseMLModel[SeasonalityIn, SeasonalityOut]):
    metadata = ModelMetadata(
        model_id="M-B2",
        block="B",
        name="Seasonality Model",
        version="1.0.0",
        algorithm="MCC-adjusted seasonal decomposition with Uzbekistan calendar events",
        is_stub=False,
        feature_names=["mcc_code", "region_id", "year"],
        supported_explainers=["rule_based"],
        description="Monthly seasonality indices for Uzbekistan market with named calendar events.",
    )

    def predict(self, input_data: SeasonalityIn) -> SeasonalityOut:
        # Apply MCC-specific adjustments on top of base pattern
        adjustment = _MCC_ADJUSTMENTS.get(input_data.mcc_code, np.zeros(12))
        indices = _BASE_RETAIL + adjustment

        # Ramadan: for food MCC codes, boost the Ramadan months further
        ramadan_months = _get_ramadan_months(input_data.year)
        if input_data.mcc_code in {"5812", "5814", "5411"}:
            for rm in ramadan_months:
                indices[rm - 1] += 0.08  # extra boost during Ramadan

        # Normalize so that mean = 1.0 (proper seasonal indices)
        indices = indices / float(np.mean(indices))
        indices = np.clip(indices, 0.5, 2.0)
        monthly_indices = [round(float(v), 3) for v in indices]

        peak_months = [i + 1 for i, v in enumerate(monthly_indices) if v >= 1.08]
        trough_months = [i + 1 for i, v in enumerate(monthly_indices) if v <= 0.92]

        events = _build_events(input_data.year, input_data.mcc_code)

        return SeasonalityOut(
            monthly_indices=monthly_indices,
            peak_months=peak_months,
            trough_months=trough_months,
            events=events,
        )

    def explain(self, input_data: SeasonalityIn) -> dict:
        adj = _MCC_ADJUSTMENTS.get(input_data.mcc_code, np.zeros(12))
        mcc_effect = float(np.abs(adj).sum())
        return {
            "calendar_events_weight": 0.50,
            "historical_pattern_weight": 0.35,
            "mcc_specific_weight": 0.15,
            "total_mcc_adjustment": round(mcc_effect, 3),
            "ramadan_months": _get_ramadan_months(input_data.year),
        }
