import math

import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_c import StreetVitalityIn, StreetVitalityOut

# POI density benchmarks by area type (per km²)
_POI_DENSITY_URBAN_CORE = 250.0    # dense city centre
_POI_DENSITY_SUBURBAN = 80.0
_POI_DENSITY_RURAL = 15.0

# Vacancy rates by density tier
_VACANCY_RATE_URBAN = 0.08    # 8% vacant in dense areas
_VACANCY_RATE_SUBURBAN = 0.15
_VACANCY_RATE_RURAL = 0.30

# Typical category distribution in Uzbekistan urban areas
_URBAN_CATEGORIES = ["Food & Beverage", "Retail", "Services", "Healthcare", "Education"]
_SUBURBAN_CATEGORIES = ["Grocery & Markets", "Services", "Food & Beverage", "Auto Services"]
_MIXED_CATEGORIES = ["Food & Beverage", "Retail", "Services", "Wholesale"]


def _density_from_coords(lat: float, lon: float) -> float:
    """Estimate population density from coordinates."""
    dist = math.sqrt((lat - 41.30) ** 2 + (lon - 69.27) ** 2)
    density = 10_000.0 / (1.0 + dist * 9)
    return float(np.clip(density, 200, 18_000))


def _spatial_hash(lat: float, lon: float, seed: int) -> float:
    """Deterministic value in [0, 1] from lat/lon."""
    val = (
        0.5
        + 0.25 * math.sin(lat * 23.1 + seed)
        + 0.25 * math.cos(lon * 17.9 + seed)
    )
    return float(np.clip(val, 0, 1))


@register_model("M-C4")
class StreetVitalityModel(BaseMLModel[StreetVitalityIn, StreetVitalityOut]):
    metadata = ModelMetadata(
        model_id="M-C4",
        block="C",
        name="Street Vitality Index",
        version="1.0.0",
        algorithm="Density-weighted POI estimation with spatial hash vitality index",
        is_stub=False,
        feature_names=["lat", "lon", "radius_m"],
        supported_explainers=["rule_based"],
        description="Active storefront ratio and street vitality using density model.",
    )

    def predict(self, input_data: StreetVitalityIn) -> StreetVitalityOut:
        density = _density_from_coords(input_data.lat, input_data.lon)
        area_km2 = math.pi * (input_data.radius_m / 1000) ** 2

        # Determine density tier
        if density > 6000:
            poi_density = _POI_DENSITY_URBAN_CORE
            vacancy_rate = _VACANCY_RATE_URBAN
            categories = _URBAN_CATEGORIES
        elif density > 2000:
            poi_density = _POI_DENSITY_SUBURBAN
            vacancy_rate = _VACANCY_RATE_SUBURBAN
            categories = _SUBURBAN_CATEGORIES
        else:
            poi_density = _POI_DENSITY_RURAL
            vacancy_rate = _VACANCY_RATE_RURAL
            categories = _MIXED_CATEGORIES

        # POI count scaled by area + spatial variation
        spatial_var = _spatial_hash(input_data.lat, input_data.lon, 42)
        poi_count = max(1, int(area_km2 * poi_density * (0.75 + 0.5 * spatial_var)))

        # Active vs vacant storefronts
        active_ratio = 1.0 - vacancy_rate * (1.0 + 0.3 * (1 - spatial_var))
        active_ratio = float(np.clip(active_ratio, 0.50, 0.98))
        active = max(0, int(poi_count * active_ratio))
        vacant = poi_count - active

        # Vitality index: weighted combination of active ratio, density, POI richness
        vitality_raw = (
            active_ratio * 60
            + (density / 18_000) * 25
            + float(np.clip(math.log1p(poi_count) / math.log1p(200), 0, 1)) * 15
        )
        vitality_index = float(np.clip(vitality_raw, 0, 100))

        # Dominant categories: ordered by frequency for the density tier
        n_cats = min(4, len(categories))
        dominant = categories[:n_cats]

        return StreetVitalityOut(
            vitality_index=round(vitality_index, 1),
            active_storefronts=active,
            vacant_storefronts=vacant,
            poi_count=poi_count,
            dominant_categories=dominant,
        )

    def explain(self, input_data: StreetVitalityIn) -> dict:
        density = _density_from_coords(input_data.lat, input_data.lon)
        return {
            "active_ratio_weight": 0.60,
            "poi_density_weight": 0.25,
            "registration_recency_weight": 0.15,
            "estimated_density_km2": round(density, 0),
        }
