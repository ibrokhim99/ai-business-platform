import math

import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_c import LocationScoreIn, LocationScoreOut

# Sub-score weights (must sum to 1.0)
_WEIGHTS = {
    "traffic": 0.20,
    "competition": 0.15,
    "vitality": 0.15,
    "anchor": 0.12,
    "visibility": 0.12,
    "isochrone": 0.10,
    "demographic": 0.10,
    "income": 0.06,
}

# MCC-specific weight adjustments — some metrics matter more for certain businesses
_MCC_WEIGHT_OVERRIDE: dict[str, dict[str, float]] = {
    "5812": {"traffic": 0.25, "anchor": 0.15, "competition": 0.12},  # Restaurant: traffic & anchor matter most
    "5411": {"demographic": 0.15, "isochrone": 0.15, "traffic": 0.18},  # Grocery: catchment matters most
    "5912": {"demographic": 0.15, "income": 0.10, "isochrone": 0.12},   # Pharmacy: demographics key
    "7372": {"income": 0.12, "demographic": 0.15, "traffic": 0.15},     # Software: income matters
}

# Uzbekistan urban density grid: approximate population density by lat band
# Tashkent region: lat ~41.3°, high density; rural areas lower density
def _estimate_density(lat: float, lon: float) -> float:
    """Estimate population density (people/km²) from coordinates."""
    # Tashkent centroid: 41.30°N, 69.27°E
    dist_to_tashkent = math.sqrt((lat - 41.30) ** 2 + (lon - 69.27) ** 2)
    # Density decreases with distance from urban centre (inverse square)
    density = 8000.0 / (1.0 + dist_to_tashkent * 12)
    return float(np.clip(density, 200, 18000))


def _spatial_hash_score(lat: float, lon: float, seed_offset: int, base: float = 60.0, spread: float = 25.0) -> float:
    """Deterministic score from lat/lon using trigonometric spatial hash."""
    # Use Fourier-style combination of lat/lon at different frequencies
    score = (
        base
        + spread * 0.35 * math.sin(lat * 17.3 + seed_offset)
        + spread * 0.35 * math.cos(lon * 13.7 + seed_offset)
        + spread * 0.15 * math.sin((lat + lon) * 7.1 + seed_offset)
        + spread * 0.15 * math.cos((lat - lon) * 5.3 + seed_offset)
    )
    return float(np.clip(score, 0, 100))


def _compute_sub_scores(
    lat: float, lon: float, mcc_code: str, radius_m: int
) -> dict[str, float]:
    density = _estimate_density(lat, lon)
    density_norm = float(np.clip(density / 12000.0, 0, 1))

    # Traffic: density + spatial variation
    traffic = float(np.clip(
        density_norm * 60 + _spatial_hash_score(lat, lon, 1, base=20, spread=30),
        10, 98,
    ))

    # Competition: inverse saturation proxy — busier areas have more competition
    # High traffic → lower competition score (harder to capture share)
    competition = float(np.clip(100 - traffic * 0.65 + _spatial_hash_score(lat, lon, 2, base=0, spread=15), 10, 95))

    # Vitality: active storefronts proxy
    vitality = float(np.clip(
        density_norm * 50 + _spatial_hash_score(lat, lon, 3, base=30, spread=30),
        10, 97,
    ))

    # Anchor effect: proximity to commercial anchors
    anchor = float(np.clip(
        _spatial_hash_score(lat, lon, 4, base=45, spread=35),
        5, 95,
    ))

    # Visibility: based on grid position (urban cores tend to have better visibility)
    visibility = float(np.clip(
        density_norm * 40 + _spatial_hash_score(lat, lon, 5, base=40, spread=25),
        10, 97,
    ))

    # Isochrone: catchment population within walking distance, scaled
    walk_radius_m = radius_m * 2
    area_km2 = math.pi * (walk_radius_m / 1000) ** 2
    catchment_pop = area_km2 * density
    isochrone = float(np.clip(
        math.log1p(catchment_pop) / math.log1p(50000) * 80 + _spatial_hash_score(lat, lon, 6, base=0, spread=15),
        5, 95,
    ))

    # Demographic: working-age population richness (correlated with density)
    demographic = float(np.clip(
        density_norm * 55 + _spatial_hash_score(lat, lon, 7, base=25, spread=25),
        10, 95,
    ))

    # Income: approximate disposable income index
    income = float(np.clip(
        density_norm * 50 + _spatial_hash_score(lat, lon, 8, base=30, spread=25),
        10, 95,
    ))

    return {
        "traffic": round(traffic, 1),
        "competition": round(competition, 1),
        "vitality": round(vitality, 1),
        "anchor": round(anchor, 1),
        "visibility": round(visibility, 1),
        "isochrone": round(isochrone, 1),
        "demographic": round(demographic, 1),
        "income": round(income, 1),
    }


@register_model("M-C1")
class LocationScoreModel(BaseMLModel[LocationScoreIn, LocationScoreOut]):
    metadata = ModelMetadata(
        model_id="M-C1",
        block="C",
        name="Location Score",
        version="1.0.0",
        algorithm="Weighted composite 8-factor model with MCC-adjusted weights",
        is_stub=False,
        feature_names=["lat", "lon", "mcc_code", "radius_m"],
        supported_explainers=["rule_based"],
        description="Integral location attractiveness score 0–100 with 8 sub-dimensions.",
    )

    def predict(self, input_data: LocationScoreIn) -> LocationScoreOut:
        sub = _compute_sub_scores(
            input_data.lat, input_data.lon, input_data.mcc_code, input_data.radius_m
        )

        # Apply MCC-specific weight adjustments
        weights = dict(_WEIGHTS)
        mcc_override = _MCC_WEIGHT_OVERRIDE.get(input_data.mcc_code, {})
        if mcc_override:
            # Merge overrides, then renormalize to sum=1
            weights.update(mcc_override)
            total = sum(weights.values())
            weights = {k: v / total for k, v in weights.items()}

        score = float(np.clip(
            sum(sub[k] * weights[k] for k in sub),
            0, 100,
        ))

        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"

        if score >= 85:
            recommendation = "Excellent location — high priority for site acquisition."
        elif score >= 70:
            recommendation = "Good location with strong fundamentals — proceed with standard due diligence."
        elif score >= 55:
            recommendation = "Moderate location — address weak sub-scores before committing."
        else:
            recommendation = "Below-average location — significant risks; consider alternative sites."

        return LocationScoreOut(
            score=round(score, 1),
            grade=grade,
            sub_scores=sub,
            recommendation=recommendation,
        )

    def explain(self, input_data: LocationScoreIn) -> dict:
        weights = dict(_WEIGHTS)
        mcc_override = _MCC_WEIGHT_OVERRIDE.get(input_data.mcc_code, {})
        if mcc_override:
            weights.update(mcc_override)
            total = sum(weights.values())
            weights = {k: round(v / total, 4) for k, v in weights.items()}
        return {
            "sub_score_weights": weights,
            "density_estimate_km2": round(_estimate_density(input_data.lat, input_data.lon), 0),
            "mcc_weight_override_applied": bool(mcc_override),
        }
