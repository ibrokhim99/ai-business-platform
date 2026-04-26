import math

import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_c import AnchorEffectIn, AnchorEffectOut

# Anchor type definitions: mass (relative importance) and typical radius of influence (km)
_ANCHOR_TYPES: dict[str, dict] = {
    "regional_mall":    {"mass": 10.0, "influence_km": 3.0},
    "shopping_center":  {"mass": 6.0,  "influence_km": 1.5},
    "bazaar":           {"mass": 7.0,  "influence_km": 1.0},
    "supermarket":      {"mass": 4.0,  "influence_km": 0.8},
    "mosque":           {"mass": 3.0,  "influence_km": 0.5},
    "university":       {"mass": 5.0,  "influence_km": 1.0},
    "hospital":         {"mass": 4.5,  "influence_km": 1.0},
    "transit_hub":      {"mass": 6.0,  "influence_km": 0.6},
    "government":       {"mass": 3.0,  "influence_km": 0.5},
    "hotel":            {"mass": 3.5,  "influence_km": 0.7},
}

# Synthetic anchor catalogue: seeded from coordinate quadrant
# In production this would come from a POI database
_SYNTHETIC_ANCHOR_TEMPLATES = [
    {"name": "Tashkent City Mall", "type": "regional_mall",   "base_lat": 41.30, "base_lon": 69.27},
    {"name": "Mega Planet",        "type": "shopping_center", "base_lat": 41.36, "base_lon": 69.32},
    {"name": "Chorsu Bazaar",      "type": "bazaar",          "base_lat": 41.32, "base_lon": 69.23},
    {"name": "Olmazor Bazaar",     "type": "bazaar",          "base_lat": 41.33, "base_lon": 69.20},
    {"name": "Korzinka Superstore","type": "supermarket",     "base_lat": 41.28, "base_lon": 69.25},
    {"name": "Makro Hypermarket",  "type": "supermarket",     "base_lat": 41.31, "base_lon": 69.30},
    {"name": "TATU University",    "type": "university",      "base_lat": 41.34, "base_lon": 69.28},
    {"name": "Republican Hospital","type": "hospital",        "base_lat": 41.29, "base_lon": 69.27},
    {"name": "Tashkent Station",   "type": "transit_hub",     "base_lat": 41.29, "base_lon": 69.24},
    {"name": "Khamza Metro",       "type": "transit_hub",     "base_lat": 41.30, "base_lon": 69.26},
    {"name": "Juma Mosque",        "type": "mosque",          "base_lat": 41.32, "base_lon": 69.22},
    {"name": "City Hotel Tashkent","type": "hotel",           "base_lat": 41.30, "base_lon": 69.28},
]

_EARTH_RADIUS_M = 6_371_000.0


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return _EARTH_RADIUS_M * 2 * math.asin(math.sqrt(a))


@register_model("M-C5")
class AnchorEffectModel(BaseMLModel[AnchorEffectIn, AnchorEffectOut]):
    metadata = ModelMetadata(
        model_id="M-C5",
        block="C",
        name="Anchor Effect Model",
        version="1.0.0",
        algorithm="Newton gravity model with multi-anchor superposition",
        is_stub=False,
        feature_names=["lat", "lon", "radius_m"],
        supported_explainers=["rule_based"],
        description="Traffic lift from nearby anchor points using Newton gravity model.",
    )

    def predict(self, input_data: AnchorEffectIn) -> AnchorEffectOut:
        anchors_in_range = []
        total_gravity = 0.0

        for template in _SYNTHETIC_ANCHOR_TEMPLATES:
            # Add small deterministic offset per anchor to simulate realistic spread
            lat_offset = math.sin(hash(template["name"]) % 1000) * 0.03
            lon_offset = math.cos(hash(template["name"]) % 1000) * 0.04
            anchor_lat = template["base_lat"] + lat_offset
            anchor_lon = template["base_lon"] + lon_offset

            dist_m = _haversine_m(input_data.lat, input_data.lon, anchor_lat, anchor_lon)
            if dist_m > input_data.radius_m:
                continue

            atype = template["type"]
            params = _ANCHOR_TYPES.get(atype, {"mass": 2.0, "influence_km": 0.5})
            mass = params["mass"]

            # Gravity: G = mass / distance^2 (Newton gravity model)
            # Use distance in hundreds of metres to keep values manageable
            dist_hundreds = max(dist_m / 100.0, 1.0)
            gravity = mass / (dist_hundreds ** 2)

            # Normalize gravity_score to [0, 1] using influence zone
            influence_m = params["influence_km"] * 1000
            gravity_score = float(np.clip(
                1.0 - dist_m / influence_m,
                0.0, 1.0,
            ))

            anchors_in_range.append({
                "name": template["name"],
                "type": atype,
                "distance_m": round(dist_m, 0),
                "gravity_score": round(gravity_score, 3),
            })
            total_gravity += gravity

        # Anchor boost: sigmoid-normalized total gravity
        if anchors_in_range:
            # Cap boost at ~50%
            boost_raw = float(total_gravity / 10.0 * 100)  # gravity → pct
            anchor_boost_pct = float(np.clip(boost_raw, 0, 50))
            # Dominant anchor = highest gravity_score
            dominant = max(anchors_in_range, key=lambda a: a["gravity_score"])["name"]
        else:
            anchor_boost_pct = 0.0
            dominant = None

        return AnchorEffectOut(
            anchor_boost_pct=round(anchor_boost_pct, 1),
            anchors=sorted(anchors_in_range, key=lambda a: a["distance_m"]),
            dominant_anchor=dominant,
        )

    def explain(self, input_data: AnchorEffectIn) -> dict:
        return {
            "anchor_gravity_weight": 0.60,
            "distance_decay_weight": 0.30,
            "anchor_type_weight": 0.10,
            "model": "Newton_gravity_superposition",
            "anchor_types_considered": list(_ANCHOR_TYPES.keys()),
        }
