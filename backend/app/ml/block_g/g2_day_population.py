import math

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_g import DayPopulationIn, DayPopulationOut

# Weekday (Mon-Fri) hourly relative activity weights (24 values)
_WEEKDAY_WEIGHTS = [
    0.15, 0.08, 0.05, 0.05, 0.08, 0.25,   # 00-05: night → early morning
    0.55, 0.85, 1.00, 0.95, 0.90, 0.88,   # 06-11: morning rush → mid morning
    0.85, 0.80, 0.78, 0.82, 0.92, 1.00,   # 12-17: lunch → afternoon → evening rush
    0.95, 0.80, 0.68, 0.52, 0.38, 0.22,   # 18-23: evening → late night
]

# Weekend hourly weights (Sat-Sun): later start, longer afternoon/evening
_WEEKEND_WEIGHTS = [
    0.18, 0.10, 0.07, 0.05, 0.07, 0.12,   # 00-05
    0.22, 0.38, 0.55, 0.70, 0.82, 0.90,   # 06-11: slow morning
    0.95, 0.98, 1.00, 0.98, 0.95, 0.92,   # 12-17: busy afternoon
    0.88, 0.82, 0.72, 0.58, 0.42, 0.28,   # 18-23: evening wind-down
]

# Gravity model base densities (people per km²)
_RESIDENT_DENSITY = 5_000
_WORKER_DENSITY_WEEKDAY = 2_500
_WORKER_DENSITY_WEEKEND = 500
_VISITOR_DENSITY_WEEKDAY = 800
_VISITOR_DENSITY_WEEKEND = 1_200
_TRANSIT_DENSITY_WEEKDAY = 1_400
_TRANSIT_DENSITY_WEEKEND = 600


@register_model("M-G2")
class DayPopulationModel(BaseMLModel[DayPopulationIn, DayPopulationOut]):
    metadata = ModelMetadata(
        model_id="M-G2", block="G",
        name="Day Population Estimator",
        version="1.0.0",
        algorithm="Gravity model with day-of-week + hourly profiles",
        is_stub=False,
        feature_names=["lat", "lon", "radius_m", "hour_of_day", "day_of_week"],
        supported_explainers=["rule_based"],
        description="Daily audience: residents + workers + visitors + transit.",
    )

    def predict(self, input_data: DayPopulationIn) -> DayPopulationOut:
        area_km2 = math.pi * (input_data.radius_m / 1000) ** 2
        is_weekend = input_data.day_of_week >= 5   # 5=Sat, 6=Sun

        residents = int(area_km2 * _RESIDENT_DENSITY)
        workers = int(area_km2 * (
            _WORKER_DENSITY_WEEKEND if is_weekend else _WORKER_DENSITY_WEEKDAY
        ))
        visitors = int(area_km2 * (
            _VISITOR_DENSITY_WEEKEND if is_weekend else _VISITOR_DENSITY_WEEKDAY
        ))
        transit = int(area_km2 * (
            _TRANSIT_DENSITY_WEEKEND if is_weekend else _TRANSIT_DENSITY_WEEKDAY
        ))
        total = residents + workers + visitors + transit

        hour_weights = _WEEKEND_WEIGHTS if is_weekend else _WEEKDAY_WEIGHTS
        hourly = [int(total * w) for w in hour_weights]

        return DayPopulationOut(
            residents=residents,
            workers=workers,
            visitors=visitors,
            transit_passers=transit,
            total_population=total,
            hourly_profile=hourly,
        )

    def explain(self, input_data: DayPopulationIn) -> dict:
        return {
            "residential_density": 0.40,
            "commercial_density": 0.35,
            "transit_proximity": 0.25,
        }
