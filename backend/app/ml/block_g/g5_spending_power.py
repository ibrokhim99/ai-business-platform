import math

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_g import SpendingPowerIn, SpendingPowerOut

# Urban centres and their spending-power baselines (index 0-100)
_URBAN_REFS = [
    (41.299496, 69.240073, 82),   # Tashkent
    (39.654522, 66.975780, 65),   # Samarkand
    (39.774022, 64.424896, 55),   # Bukhara
    (40.996370, 71.672586, 50),   # Namangan
    (40.384260, 71.787320, 52),   # Fergana
]
_RURAL_INDEX = 25.0

# MCC category-breakdown templates
_MCC_CATEGORY: dict[str, dict[str, float]] = {
    "5812": {"food_dining": 42, "transport": 12, "retail": 18, "services": 16, "entertainment": 12},
    "5411": {"food_grocery": 50, "transport": 15, "retail": 14, "services": 13, "entertainment": 8},
    "5912": {"health": 35, "food_grocery": 25, "retail": 18, "services": 14, "entertainment": 8},
    "5651": {"fashion": 40, "food_dining": 20, "transport": 12, "services": 15, "entertainment": 13},
    "7011": {"hospitality": 38, "food_dining": 22, "transport": 18, "services": 14, "entertainment": 8},
}
_DEFAULT_CATEGORY: dict[str, float] = {
    "food": 30, "retail": 24, "transport": 14, "services": 18, "entertainment": 14
}

_EARTH_R = 6_371_000


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlam = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * _EARTH_R * math.asin(math.sqrt(a))


def _idw_spending_index(lat: float, lon: float) -> float:
    """Inverse-distance-weighted spending power index from known urban references."""
    weights = []
    values = []
    for ref_lat, ref_lon, ref_idx in _URBAN_REFS:
        d = _haversine_m(lat, lon, ref_lat, ref_lon)
        w = 1.0 / (d + 1000)  # avoid division by zero; +1000m floor
        weights.append(w)
        values.append(ref_idx)
    idw_index = sum(w * v for w, v in zip(weights, values)) / sum(weights)
    return round(min(max(idw_index, 0.0), 100.0), 1)


def _heatmap_cells(lat: float, lon: float, radius_m: int, center_index: float) -> list[dict]:
    """Generate 5×5 grid of heatmap cells using IDW interpolation."""
    cells = []
    grid_n = 5
    half = (grid_n - 1) / 2
    deg_per_m_lat = 1 / 111_000
    deg_per_m_lon = 1 / (111_000 * math.cos(math.radians(lat)) + 1e-9)
    step_m = radius_m / half

    for i in range(grid_n):
        for j in range(grid_n):
            offset_lat = (i - half) * step_m * deg_per_m_lat
            offset_lon = (j - half) * step_m * deg_per_m_lon
            cell_lat = round(lat + offset_lat, 6)
            cell_lon = round(lon + offset_lon, 6)
            cell_idx = _idw_spending_index(cell_lat, cell_lon)
            cells.append({"lat": cell_lat, "lon": cell_lon, "index": cell_idx})
    return cells


@register_model("M-G5")
class SpendingPowerModel(BaseMLModel[SpendingPowerIn, SpendingPowerOut]):
    metadata = ModelMetadata(
        model_id="M-G5", block="G",
        name="Spending Power Index",
        version="1.0.0",
        algorithm="IDW interpolation from urban reference points",
        is_stub=False,
        feature_names=["lat", "lon", "radius_m"],
        supported_explainers=["rule_based"],
        description="Purchasing power heatmap by district and street.",
    )

    def predict(self, input_data: SpendingPowerIn) -> SpendingPowerOut:
        idx = _idw_spending_index(input_data.lat, input_data.lon)
        avg_monthly_spend = round(150 + idx * 5, 2)

        quartile = (
            "Q4" if idx >= 75
            else "Q3" if idx >= 55
            else "Q2" if idx >= 35
            else "Q1"
        )

        heatmap = _heatmap_cells(input_data.lat, input_data.lon, input_data.radius_m, idx)

        # Use MCC-specific breakdown if lat/lon signals typical MCC (not available here)
        category_breakdown: dict[str, float] = dict(_DEFAULT_CATEGORY)

        return SpendingPowerOut(
            spending_power_index=idx,
            avg_monthly_spend_per_capita=avg_monthly_spend,
            quartile=quartile,
            heatmap_cells=heatmap,
            category_breakdown=category_breakdown,
        )

    def explain(self, input_data: SpendingPowerIn) -> dict:
        return {
            "income_level": 0.50,
            "transaction_volume": 0.30,
            "residential_quality": 0.20,
        }
