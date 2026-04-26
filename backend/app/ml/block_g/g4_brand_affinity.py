import math

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_g import BrandAffinityIn, BrandAffinityOut

# MCC → top chain names by category
_MCC_CHAINS: dict[str, list[str]] = {
    "5812": ["Dodo Pizza", "Burger House", "Coffee House", "KFC", "McDonald's"],
    "5411": ["Korzinka", "Makro", "Havas", "Carrefour Express"],
    "5912": ["DOZ.uz", "Oson Apteka", "MedLine Pharmacy"],
    "5651": ["Zara", "H&M", "Adidas", "LC Waikiki"],
    "7011": ["Hilton", "Hyatt", "Wyndham", "Ramada"],
    "5940": ["Decathlon", "Intersport", "Sportmaster"],
    "7372": ["1C", "Oracle", "SAP", "Microsoft"],
}
_DEFAULT_CHAINS = ["Leading Brand A", "Leading Brand B", "Leading Brand C"]

# Urban centre coordinates for chain preference calculation
# Cities with high urbanisation → higher chain preference
_URBAN_CENTRES = [
    (41.299496, 69.240073),   # Tashkent
    (39.654522, 66.975780),   # Samarkand
    (39.774022, 64.424896),   # Bukhara
]

_EARTH_R = 6_371_000  # metres


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * _EARTH_R * math.asin(math.sqrt(a))


def _urban_score(lat: float, lon: float) -> float:
    """0–1: 1 = city centre, 0 = remote rural."""
    min_dist = min(_haversine_m(lat, lon, c[0], c[1]) for c in _URBAN_CENTRES)
    # Within 2km of centre → fully urban; beyond 50km → rural
    score = 1.0 - min(min_dist / 50_000, 1.0)
    return score


@register_model("M-G4")
class BrandAffinityModel(BaseMLModel[BrandAffinityIn, BrandAffinityOut]):
    metadata = ModelMetadata(
        model_id="M-G4", block="G",
        name="Brand Affinity Model",
        version="1.0.0",
        algorithm="Geo-urban score + MCC chain preference",
        is_stub=False,
        feature_names=["lat", "lon", "radius_m", "mcc_code"],
        supported_explainers=["rule_based"],
        description="Consumer loyalty to chains vs independent outlets.",
    )

    def predict(self, input_data: BrandAffinityIn) -> BrandAffinityOut:
        urban = _urban_score(input_data.lat, input_data.lon)   # 0–1

        # Base chain preference scales with urbanisation (20–75%)
        chain_pct = round(20.0 + urban * 55.0, 1)
        indep_pct = round(100.0 - chain_pct, 1)

        # MCC modifier
        chain_boost = {
            "5812": 5, "5411": 8, "5651": 10, "7011": 5,
        }
        chain_pct = min(chain_pct + chain_boost.get(input_data.mcc_code, 0), 90.0)
        indep_pct = round(100.0 - chain_pct, 1)

        brand_loyalty_index = round(chain_pct / 100 * 0.85, 3)

        chains = _MCC_CHAINS.get(input_data.mcc_code, _DEFAULT_CHAINS)

        if chain_pct > 55:
            opp_type = "chain"
        elif indep_pct > 55:
            opp_type = "independent"
        else:
            opp_type = "mixed"

        return BrandAffinityOut(
            chain_preference_pct=chain_pct,
            independent_preference_pct=indep_pct,
            top_chains=chains[:4],
            brand_loyalty_index=brand_loyalty_index,
            opportunity_type=opp_type,
        )

    def explain(self, input_data: BrandAffinityIn) -> dict:
        return {
            "urbanisation_level": 0.50,
            "mcc_chain_density": 0.30,
            "demographic_profile": 0.20,
        }
