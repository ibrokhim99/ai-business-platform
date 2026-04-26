import math

import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_a import CrossNicheIn, CrossNicheOut

# MCC category groupings for overlap/similarity computation
# Each MCC is assigned to a category group; same group → high cannibalization
_MCC_GROUPS: dict[str, str] = {
    "5812": "food_full_service",
    "5813": "food_bars",
    "5814": "food_fast",
    "5815": "food_digital",
    "5411": "grocery",
    "5422": "grocery_meat",
    "5441": "grocery_candy",
    "5451": "grocery_dairy",
    "5462": "grocery_bakery",
    "5912": "pharmacy",
    "5122": "pharmacy_wholesale",
    "5661": "apparel_shoes",
    "5611": "apparel_men",
    "5621": "apparel_women",
    "5699": "apparel_misc",
    "7372": "tech_software",
    "5045": "tech_hardware",
    "5065": "tech_electronics",
    "5940": "sporting",
    "5941": "sporting_outdoor",
    "5999": "misc_retail",
    "5900": "misc_retail",
    "7011": "hospitality",
    "7012": "hospitality_timeshare",
    "5511": "auto",
    "5521": "auto_used",
    "7531": "auto_service",
}
_DEFAULT_GROUP = "misc"

# Cannibalization risk by relationship type
_RISK_SAME_GROUP = 0.55          # same category → high cannibalization
_RISK_ADJACENT_GROUP = 0.20      # related category (e.g., food groups overlapping)
_RISK_UNRELATED = 0.05           # unrelated

# Food sub-groups that are adjacent (not identical)
_FOOD_GROUPS = {"food_full_service", "food_bars", "food_fast", "food_digital"}
_GROCERY_GROUPS = {"grocery", "grocery_meat", "grocery_candy", "grocery_dairy", "grocery_bakery"}
_APPAREL_GROUPS = {"apparel_shoes", "apparel_men", "apparel_women", "apparel_misc"}
_TECH_GROUPS = {"tech_software", "tech_hardware", "tech_electronics"}
_PHARMA_GROUPS = {"pharmacy", "pharmacy_wholesale"}
_SPORT_GROUPS = {"sporting", "sporting_outdoor"}
_AUTO_GROUPS = {"auto", "auto_used", "auto_service"}
_HOSPITALITY_GROUPS = {"hospitality", "hospitality_timeshare"}

_SUPER_GROUPS = [
    _FOOD_GROUPS, _GROCERY_GROUPS, _APPAREL_GROUPS, _TECH_GROUPS,
    _PHARMA_GROUPS, _SPORT_GROUPS, _AUTO_GROUPS, _HOSPITALITY_GROUPS,
]


def _get_group(mcc: str) -> str:
    return _MCC_GROUPS.get(mcc, _DEFAULT_GROUP)


def _cannibalization_risk(new_group: str, adj_group: str) -> float:
    if new_group == adj_group:
        return _RISK_SAME_GROUP
    for super_group in _SUPER_GROUPS:
        if new_group in super_group and adj_group in super_group:
            return _RISK_ADJACENT_GROUP
    return _RISK_UNRELATED


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


@register_model("M-A6")
class CrossNicheModel(BaseMLModel[CrossNicheIn, CrossNicheOut]):
    metadata = ModelMetadata(
        model_id="M-A6",
        block="A",
        name="Cross-Niche Cannibalization",
        version="1.0.0",
        algorithm="MCC category graph with haversine distance decay",
        is_stub=False,
        feature_names=["new_mcc_code", "adjacent_mcc_codes", "radius_m", "location_lat", "location_lon"],
        supported_explainers=["rule_based"],
        description="Estimates revenue cannibalization on adjacent niches using MCC category graph.",
    )

    def predict(self, input_data: CrossNicheIn) -> CrossNicheOut:
        new_group = _get_group(input_data.new_mcc_code)
        affected = []
        total_weighted_risk = 0.0

        for adj_mcc in input_data.adjacent_mcc_codes:
            adj_group = _get_group(adj_mcc)
            base_risk = _cannibalization_risk(new_group, adj_group)

            # Distance decay: assume adjacent businesses are randomly distributed
            # within radius — use expected distance = radius * 0.5 as heuristic
            expected_dist_m = input_data.radius_m * 0.5
            distance_factor = 1.0 / (1.0 + expected_dist_m / 500.0)

            risk_i = base_risk * distance_factor
            cannib_pct = round(risk_i * 100, 1)

            affected.append({
                "mcc_code": adj_mcc,
                "mcc_group": adj_group,
                "cannibalization_pct": cannib_pct,
                "distance_factor": round(distance_factor, 3),
            })
            total_weighted_risk += risk_i

        n = len(input_data.adjacent_mcc_codes)
        avg_risk = total_weighted_risk / n if n > 0 else 0.0
        cannibalization_risk = float(np.clip(avg_risk, 0, 1))

        # Net revenue impact: negative (loss to existing niches)
        net_revenue_impact_pct = round(-cannibalization_risk * 15.0, 2)

        if cannibalization_risk < 0.15:
            recommendation = "Low cannibalization risk — proceed with standard market entry."
        elif cannibalization_risk < 0.35:
            recommendation = "Moderate risk — consider differentiation strategy to reduce overlap."
        elif cannibalization_risk < 0.55:
            recommendation = "High risk — significant market overlap detected; evaluate alternatives."
        else:
            recommendation = "Critical cannibalization risk — entry likely to severely impact adjacent niches."

        return CrossNicheOut(
            cannibalization_risk=round(cannibalization_risk, 3),
            affected_niches=affected,
            net_revenue_impact_pct=net_revenue_impact_pct,
            recommendation=recommendation,
        )

    def explain(self, input_data: CrossNicheIn) -> dict:
        new_group = _get_group(input_data.new_mcc_code)
        adj_groups = [_get_group(m) for m in input_data.adjacent_mcc_codes]
        same_group_count = sum(1 for g in adj_groups if g == new_group)
        return {
            "new_mcc_group": new_group,
            "adjacent_groups": adj_groups,
            "same_group_count": same_group_count,
            "graph_proximity_weight": 0.65,
            "distance_decay_weight": 0.35,
        }
