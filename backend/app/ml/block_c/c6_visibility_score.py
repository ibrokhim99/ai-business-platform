import math

import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_c import VisibilityScoreIn, VisibilityScoreOut

# Cardinal direction bearing ranges
_DIRECTIONS = {
    "north": (315, 45),
    "east":  (45, 135),
    "south": (135, 225),
    "west":  (225, 315),
}

# Optimal facade directions: south and east-facing facades get most foot traffic in CIS cities
# (morning sun on east, afternoon sun on south in northern hemisphere)
_OPTIMAL_FACADE_RANGES = [(90, 210)]  # East to South-Southwest

# Common obstruction types at various coordinate patterns
_OBSTRUCTION_POOL = [
    "parked_vehicles", "utility_pole", "bus_stop_shelter",
    "adjacent_signage", "tree_canopy", "underpass_pillar", "market_stalls",
]

# Road frontage estimation: typical city block = 80-150m, corner locations have 2 facades
def _estimate_road_frontage(lat: float, lon: float) -> float:
    """Estimate road frontage width from coordinates (deterministic)."""
    # Use modular arithmetic on coordinates for variability
    val = abs(math.sin(lat * 31.7) * math.cos(lon * 19.3))
    # Urban core: 6-25m; suburban: 8-18m
    frontage = 6.0 + val * 19.0
    return round(frontage, 1)


def _estimate_sidewalk_width(lat: float, lon: float) -> float:
    """Estimate sidewalk width from coordinates."""
    val = abs(math.cos(lat * 27.1) * math.sin(lon * 21.5))
    width = 1.5 + val * 4.0  # 1.5m to 5.5m
    return round(width, 1)


def _sight_line_distances(lat: float, lon: float, facade_deg: float) -> dict[str, float]:
    """
    Compute visibility distances in 4 compass directions.
    Sight lines are longer along the facade direction and shorter perpendicular/behind.
    """
    result = {}
    for direction, (low, high) in _DIRECTIONS.items():
        # Angular difference between this direction's midpoint and facade
        mid_deg = (low + high) / 2 if high > low else (low + high + 360) / 2 % 360
        delta = min(abs(facade_deg - mid_deg), 360 - abs(facade_deg - mid_deg))

        # Sight line is longest when looking along facade direction (delta ≈ 0)
        # and shortest when looking behind (delta ≈ 180)
        base_distance = 30.0 + abs(math.sin(lat * 13.3 + lon * 7.7)) * 40
        direction_factor = math.cos(math.radians(delta)) * 0.5 + 0.5
        sight = base_distance * direction_factor

        result[direction] = round(sight, 1)
    return result


def _detect_obstructions(lat: float, lon: float, facade_deg: float) -> list[str]:
    """Select realistic obstructions based on coordinate and facade direction."""
    obstructions = []
    # Deterministic selection based on lat/lon hash
    idx1 = int(abs(lat * 100) + abs(lon * 100)) % len(_OBSTRUCTION_POOL)
    idx2 = (idx1 + int(facade_deg / 45)) % len(_OBSTRUCTION_POOL)

    # Probability of obstruction proportional to urban density
    val = abs(math.sin(lat * 19.1) * math.cos(lon * 23.7))
    if val > 0.6:
        obstructions.append(_OBSTRUCTION_POOL[idx1])
    if val > 0.75 and idx2 != idx1:
        obstructions.append(_OBSTRUCTION_POOL[idx2])

    return obstructions


def _is_optimal_facade(facade_deg: float) -> bool:
    for low, high in _OPTIMAL_FACADE_RANGES:
        if low <= facade_deg <= high:
            return True
    return False


@register_model("M-C6")
class VisibilityScoreModel(BaseMLModel[VisibilityScoreIn, VisibilityScoreOut]):
    metadata = ModelMetadata(
        model_id="M-C6",
        block="C",
        name="Visibility Score",
        version="1.0.0",
        algorithm="Geometric road frontage + facade direction visibility model",
        is_stub=False,
        feature_names=["lat", "lon", "facade_direction_deg"],
        supported_explainers=["rule_based"],
        description="Road and sidewalk visibility score using facade orientation and site geometry.",
    )

    def predict(self, input_data: VisibilityScoreIn) -> VisibilityScoreOut:
        road_frontage = _estimate_road_frontage(input_data.lat, input_data.lon)
        sidewalk_width = _estimate_sidewalk_width(input_data.lat, input_data.lon)

        sight_lines = _sight_line_distances(
            input_data.lat, input_data.lon, input_data.facade_direction_deg
        )
        obstructions = _detect_obstructions(
            input_data.lat, input_data.lon, input_data.facade_direction_deg
        )

        # Visibility score components:
        # 1. Road frontage (wider → better, 0-35 pts)
        frontage_score = float(np.clip((road_frontage / 25.0) * 35, 0, 35))

        # 2. Facade direction quality (0-30 pts)
        is_optimal = _is_optimal_facade(input_data.facade_direction_deg)
        # Partial scoring for near-optimal directions
        delta_to_south = min(
            abs(input_data.facade_direction_deg - 180),
            abs(input_data.facade_direction_deg - 90),
        )
        direction_score = float(np.clip(30 - delta_to_south * 0.15, 5, 30))

        # 3. Sight line quality: mean sight line distance (0-25 pts)
        avg_sight = float(np.mean(list(sight_lines.values())))
        sight_score = float(np.clip((avg_sight / 70) * 25, 0, 25))

        # 4. Obstruction penalty (0 to -10 pts)
        obstruction_penalty = len(obstructions) * 5.0

        # 5. Sidewalk width bonus (0-10 pts)
        sidewalk_score = float(np.clip((sidewalk_width / 5.0) * 10, 0, 10))

        raw_score = frontage_score + direction_score + sight_score + sidewalk_score - obstruction_penalty
        visibility_score = float(np.clip(raw_score, 0, 100))

        return VisibilityScoreOut(
            visibility_score=round(visibility_score, 1),
            road_frontage_m=road_frontage,
            sidewalk_width_m=sidewalk_width,
            sight_lines=sight_lines,
            obstructions=obstructions,
        )

    def explain(self, input_data: VisibilityScoreIn) -> dict:
        road_frontage = _estimate_road_frontage(input_data.lat, input_data.lon)
        is_optimal = _is_optimal_facade(input_data.facade_direction_deg)
        return {
            "road_frontage_weight": 0.35,
            "facade_direction_weight": 0.30,
            "sight_line_weight": 0.25,
            "sidewalk_width_weight": 0.10,
            "road_frontage_m": road_frontage,
            "facade_is_optimal_direction": is_optimal,
            "facade_direction_deg": input_data.facade_direction_deg,
        }
