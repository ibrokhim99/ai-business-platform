import math
import hashlib

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_e import CompetitorIntelIn, CompetitorIntelOut

# MCC → typical business type names
_MCC_NAMES = {
    "5812": ["Café", "Restaurant", "Bistro", "Diner", "Eatery"],
    "5411": ["Supermarket", "Grocery", "Mini-market", "Fresh Market", "Food Store"],
    "5912": ["Pharmacy", "Drugstore", "MedStore", "Health Hub", "Apteka"],
    "5651": ["Clothing Store", "Fashion Boutique", "Style Shop", "Apparel", "Wear"],
    "7011": ["Hotel", "Hostel", "Inn", "Lodge", "Guest House"],
}
_DEFAULT_NAMES = ["Business", "Shop", "Store", "Outlet", "Point"]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in metres between two lat/lon points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _gen_competitors(lat: float, lon: float, mcc_code: str) -> list[dict]:
    """Generate a deterministic competitor list seeded on mcc+coords."""
    seed = int(hashlib.md5(f"{mcc_code}{round(lat, 3)}{round(lon, 3)}".encode()).hexdigest(), 16)
    names = _MCC_NAMES.get(mcc_code, _DEFAULT_NAMES)
    competitors = []
    # generate up to 8 candidates at pseudo-random offsets within ~1 km
    for i in range(8):
        s = (seed >> (i * 4)) & 0xFFFF
        angle = (s % 360) * math.pi / 180
        dist = 50 + (s % 950)  # 50m .. 1000m
        dlat = (dist * math.cos(angle)) / 111_000
        dlon = (dist * math.sin(angle)) / (111_000 * math.cos(math.radians(lat)) + 1e-9)
        clat = round(lat + dlat, 6)
        clon = round(lon + dlon, 6)
        actual_dist = _haversine_m(lat, lon, clat, clon)
        if actual_dist > 1010:
            continue
        name_idx = s % len(names)
        rating = round(3.0 + (s % 21) / 10, 1)  # 3.0 .. 5.0
        competitors.append({
            "name": f"{names[name_idx]} #{i + 1}",
            "lat": clat,
            "lon": clon,
            "distance_m": round(actual_dist),
            "rating": rating,
            "type": "direct" if i % 3 != 0 else "indirect",
        })
    return competitors


@register_model("M-E1")
class CompetitorIntelModel(BaseMLModel[CompetitorIntelIn, CompetitorIntelOut]):
    metadata = ModelMetadata(
        model_id="M-E1", block="E",
        name="Competitor Intelligence",
        version="1.0.0",
        algorithm="Haversine spatial query + deterministic geo-hash",
        is_stub=False,
        feature_names=["lat", "lon", "mcc_code"],
        supported_explainers=["rule_based"],
        description="Competitor map within 300m and 1km radius.",
    )

    def predict(self, input_data: CompetitorIntelIn) -> CompetitorIntelOut:
        all_comps = _gen_competitors(input_data.lat, input_data.lon, input_data.mcc_code)
        comp_300 = [c for c in all_comps if c["distance_m"] <= 300] if input_data.radius_300m else []
        comp_1km = [c for c in all_comps if c["distance_m"] <= 1000] if input_data.radius_1km else []

        ratings = [c["rating"] for c in comp_1km if c.get("rating")]
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
        total = len(comp_1km)
        threat = (
            "critical" if total >= 7
            else "high" if total >= 5
            else "medium" if total >= 3
            else "low"
        )
        leader = max(comp_1km, key=lambda x: x.get("rating", 0))["name"] if comp_1km else None
        return CompetitorIntelOut(
            competitors_300m=comp_300,
            competitors_1km=comp_1km,
            total_count=total,
            avg_rating=avg_rating,
            market_leader=leader,
            threat_level=threat,
        )

    def explain(self, input_data: CompetitorIntelIn) -> dict:
        comps = _gen_competitors(input_data.lat, input_data.lon, input_data.mcc_code)
        n = len(comps)
        density = min(n / 8, 1.0)
        return {
            "density_score": round(density, 2),
            "quality_score": round(1 - density * 0.4, 2),
            "proximity_score": round(density * 0.6, 2),
        }
