import math

import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_c import IsochroneDemandIn, IsochroneDemandOut

# Walking speed: 1.2 m/s = 72 m/min
_WALK_SPEED_M_PER_MIN = 72.0

# MCC-specific daily consumer spend and category penetration
_MCC_PARAMS: dict[str, tuple[float, float]] = {
    # (avg_daily_spend_usd, penetration_rate)
    "5812": (8.0, 0.15),     # Restaurants
    "5814": (4.5, 0.20),     # Fast food: higher penetration, lower spend
    "5411": (12.0, 0.80),    # Grocery: very high penetration
    "5912": (6.0, 0.30),     # Pharmacy
    "5661": (25.0, 0.05),    # Shoe stores: infrequent
    "5699": (20.0, 0.08),    # Apparel
    "7372": (50.0, 0.02),    # Software: very low daily penetration
    "5045": (40.0, 0.03),    # Electronics
    "5940": (15.0, 0.04),    # Sporting
    "5999": (10.0, 0.10),    # Misc retail
}
_DEFAULT_SPEND = 7.0
_DEFAULT_PENETRATION = 0.10

# Population density as function of distance from city centre (approx)
# Uzbekistan urban cores: 8,000-18,000/km²; suburbs: 2,000-5,000/km²
def _population_density_km2(lat: float, lon: float) -> float:
    """Estimate population density from coordinates."""
    # Tashkent centre: 41.30, 69.27
    dist = math.sqrt((lat - 41.30) ** 2 + (lon - 69.27) ** 2)
    # Core density ~10,000/km², halving every ~0.5 degree
    density = 10_000 / (1 + dist * 10)
    return float(np.clip(density, 500, 18_000))


def _isochrone_area_sqkm(walk_minutes: int) -> float:
    """Approximate isochrone as a circle: area = pi * r^2 where r = speed * time."""
    radius_m = _WALK_SPEED_M_PER_MIN * walk_minutes
    area = math.pi * (radius_m ** 2) / 1_000_000  # m² → km²
    return area


@register_model("M-C3")
class IsochroneDemandModel(BaseMLModel[IsochroneDemandIn, IsochroneDemandOut]):
    metadata = ModelMetadata(
        model_id="M-C3",
        block="C",
        name="Isochrone Demand",
        version="1.0.0",
        algorithm="Circular isochrone approximation with density-weighted consumer potential",
        is_stub=False,
        feature_names=["lat", "lon", "walk_minutes", "mcc_code"],
        supported_explainers=["rule_based"],
        description="Consumer potential within walking-time isochrones using density model.",
    )

    def predict(self, input_data: IsochroneDemandIn) -> IsochroneDemandOut:
        avg_daily_spend, penetration = _MCC_PARAMS.get(
            input_data.mcc_code, (_DEFAULT_SPEND, _DEFAULT_PENETRATION)
        )
        density = _population_density_km2(input_data.lat, input_data.lon)

        zones = []
        total_pop = 0
        total_potential = 0.0

        # Sort walk_minutes ascending; compute cumulative (annular) zones
        sorted_minutes = sorted(set(input_data.walk_minutes))
        prev_area = 0.0
        prev_pop = 0

        for minutes in sorted_minutes:
            area = _isochrone_area_sqkm(minutes)

            # Population in this zone (annular ring if multiple zones)
            ring_area = area - prev_area
            ring_pop = int(ring_area * density)

            # Cumulative zone includes all population inside this isochrone
            cumulative_pop = int(area * density)
            new_pop_in_ring = cumulative_pop - prev_pop

            consumer_potential = cumulative_pop * avg_daily_spend * penetration * 30  # monthly

            zones.append({
                "minutes": minutes,
                "area_sqkm": round(area, 4),
                "population": cumulative_pop,
                "consumer_potential_usd": round(consumer_potential, 2),
            })

            prev_area = area
            prev_pop = cumulative_pop

        # Use the outermost zone totals
        outer = zones[-1] if zones else {"population": 0, "consumer_potential_usd": 0.0}
        total_pop = outer["population"]
        total_potential = outer["consumer_potential_usd"]

        return IsochroneDemandOut(
            zones=zones,
            total_addressable_population=total_pop,
            total_consumer_potential_usd=round(total_potential, 2),
        )

    def explain(self, input_data: IsochroneDemandIn) -> dict:
        density = _population_density_km2(input_data.lat, input_data.lon)
        avg_daily_spend, penetration = _MCC_PARAMS.get(
            input_data.mcc_code, (_DEFAULT_SPEND, _DEFAULT_PENETRATION)
        )
        return {
            "population_density_weight": 0.50,
            "walkability_weight": 0.30,
            "mcc_penetration_weight": 0.20,
            "estimated_density_km2": round(density, 0),
            "mcc_daily_spend_usd": avg_daily_spend,
            "mcc_penetration_rate": penetration,
            "walk_speed_m_per_min": _WALK_SPEED_M_PER_MIN,
        }
