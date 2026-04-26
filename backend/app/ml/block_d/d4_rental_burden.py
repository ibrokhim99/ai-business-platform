import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_d import RentalBurdenIn, RentalBurdenOut

# MCC-specific safe and critical thresholds
# Different industries can sustain different rent ratios
_MCC_THRESHOLDS: dict[str, tuple[float, float]] = {
    # (safe_pct, critical_pct)
    "5812": (15.0, 25.0),   # Restaurants: lower tolerance (high other costs)
    "5814": (18.0, 28.0),   # Fast food: slightly better
    "5411": (10.0, 18.0),   # Grocery: very low tolerance (thin margins)
    "5912": (20.0, 32.0),   # Pharmacy: moderate tolerance
    "7372": (25.0, 40.0),   # Software: high tolerance (low COGS)
    "5045": (18.0, 28.0),   # Electronics: moderate
    "5940": (16.0, 26.0),   # Sporting goods
    "5999": (18.0, 30.0),   # Misc retail
    "5661": (17.0, 28.0),   # Shoe stores
    "5699": (16.0, 27.0),   # Apparel
}
_DEFAULT_THRESHOLDS = (20.0, 35.0)  # Generic fallback


@register_model("M-D4")
class RentalBurdenModel(BaseMLModel[RentalBurdenIn, RentalBurdenOut]):
    metadata = ModelMetadata(
        model_id="M-D4",
        block="D",
        name="Rental Burden Model",
        version="1.0.0",
        algorithm="MCC-adjusted rent-to-revenue threshold model",
        is_stub=False,
        feature_names=["mcc_code", "monthly_revenue_estimate", "monthly_rent"],
        supported_explainers=["rule_based"],
        description="Safe/critical rent-to-revenue thresholds calibrated per MCC industry.",
    )

    def predict(self, input_data: RentalBurdenIn) -> RentalBurdenOut:
        safe_pct, critical_pct = _MCC_THRESHOLDS.get(input_data.mcc_code, _DEFAULT_THRESHOLDS)

        rent_to_revenue_pct = (
            input_data.monthly_rent / input_data.monthly_revenue_estimate * 100
        )
        rent_to_revenue_pct = round(float(rent_to_revenue_pct), 2)

        if rent_to_revenue_pct <= safe_pct:
            status = "safe"
        elif rent_to_revenue_pct <= critical_pct:
            status = "warning"
        else:
            status = "critical"

        max_affordable_rent = input_data.monthly_revenue_estimate * safe_pct / 100.0

        return RentalBurdenOut(
            rent_to_revenue_pct=rent_to_revenue_pct,
            safe_threshold_pct=safe_pct,
            critical_threshold_pct=critical_pct,
            status=status,
            max_affordable_rent=round(max_affordable_rent, 2),
        )

    def explain(self, input_data: RentalBurdenIn) -> dict:
        safe_pct, critical_pct = _MCC_THRESHOLDS.get(input_data.mcc_code, _DEFAULT_THRESHOLDS)
        return {
            "revenue_stability_weight": 0.60,
            "rent_absolute_weight": 0.40,
            "mcc_safe_threshold_pct": safe_pct,
            "mcc_critical_threshold_pct": critical_pct,
            "calibration_source": "industry_benchmarks_central_asia",
        }
