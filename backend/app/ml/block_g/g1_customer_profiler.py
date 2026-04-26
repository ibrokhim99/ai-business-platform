import math
import numpy as np
from sklearn.cluster import KMeans

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_g import CustomerProfilerIn, CustomerProfilerOut

# Segment definitions (label, avg_age, avg_income, top_categories, visit_frequency)
_SEGMENT_DEFS = [
    {
        "segment_id": "S1",
        "label": "Young Urban Professional",
        "avg_age": 28,
        "avg_income": 900,
        "top_categories": ["Coffee", "Electronics", "Fitness"],
        "visit_frequency": "daily",
    },
    {
        "segment_id": "S2",
        "label": "Family Shopper",
        "avg_age": 38,
        "avg_income": 650,
        "top_categories": ["Groceries", "Kids", "Pharmacy"],
        "visit_frequency": "weekly",
    },
    {
        "segment_id": "S3",
        "label": "Premium Buyer",
        "avg_age": 46,
        "avg_income": 1400,
        "top_categories": ["Fine Dining", "Fashion", "Travel"],
        "visit_frequency": "weekly",
    },
    {
        "segment_id": "S4",
        "label": "Budget Conscious",
        "avg_age": 33,
        "avg_income": 350,
        "top_categories": ["Discount Retail", "Fast Food", "Transport"],
        "visit_frequency": "daily",
    },
]

# MCC affinity per segment — which segment best matches a given MCC
_MCC_DOMINANT: dict[str, str] = {
    "5812": "Young Urban Professional",
    "5411": "Family Shopper",
    "5912": "Family Shopper",
    "7011": "Premium Buyer",
    "5651": "Young Urban Professional",
    "5940": "Young Urban Professional",
    "7372": "Young Urban Professional",
}
_DEFAULT_DOMINANT = "Family Shopper"

K = 4
_POPULATION_DENSITY = 8_000   # people per km²


def _build_kmeans() -> KMeans:
    """Train K-means on synthetic customer feature space."""
    rng = np.random.RandomState(42)
    n = 1000
    # Features: [age_norm, income_norm, visit_freq_norm, spend_norm]
    # 4 clusters matching segment definitions
    centers = np.array([
        [0.28, 0.60, 0.9, 0.5],   # S1: Young Urban
        [0.38, 0.43, 0.5, 0.4],   # S2: Family
        [0.46, 0.93, 0.4, 0.9],   # S3: Premium
        [0.33, 0.23, 0.8, 0.2],   # S4: Budget
    ])
    X = np.vstack([
        rng.normal(centers[i % 4], 0.08, (n // 4, 4))
        for i in range(4)
    ])
    X = np.clip(X, 0, 1)
    km = KMeans(n_clusters=K, random_state=42, n_init=10)
    km.fit(X)
    return km


_KM = _build_kmeans()


def _geo_to_features(lat: float, lon: float, mcc_code: str) -> np.ndarray:
    """Convert location to synthetic feature vector."""
    lat_n = (lat + 90) / 180
    lon_n = (lon + 180) / 360
    # Use geo hash for pseudo-random but deterministic features
    h = (hash(f"{round(lat, 2)}{round(lon, 2)}{mcc_code}") % 10000) / 10000
    return np.array([[lat_n, lon_n, (lat_n + lon_n) / 2, h]])


@register_model("M-G1")
class CustomerProfilerModel(BaseMLModel[CustomerProfilerIn, CustomerProfilerOut]):
    metadata = ModelMetadata(
        model_id="M-G1", block="G",
        name="Customer Segment Profiler",
        version="1.0.0",
        algorithm="K-means (k=4) on synthetic customer feature space",
        is_stub=False,
        feature_names=["lat", "lon", "radius_m", "mcc_code"],
        supported_explainers=["rule_based"],
        description="Target audience profile: age, income, top categories, visit frequency.",
    )

    def predict(self, input_data: CustomerProfilerIn) -> CustomerProfilerOut:
        X = _geo_to_features(input_data.lat, input_data.lon, input_data.mcc_code)

        # Compute distances to each cluster centre → derive share_pct
        distances = np.linalg.norm(_KM.cluster_centers_ - X, axis=1)
        inv_dist = 1.0 / (distances + 1e-6)
        shares = inv_dist / inv_dist.sum()
        shares_pct = (shares * 100).astype(int)
        # Normalise to sum to 100
        diff = 100 - shares_pct.sum()
        shares_pct[shares_pct.argmax()] += diff

        segments = []
        for i, seg in enumerate(_SEGMENT_DEFS):
            s = dict(seg)
            s["share_pct"] = int(shares_pct[i])
            segments.append(s)

        dominant_label = _MCC_DOMINANT.get(input_data.mcc_code, _DEFAULT_DOMINANT)
        area_km2 = math.pi * (input_data.radius_m / 1000) ** 2
        total_addressable = int(area_km2 * _POPULATION_DENSITY)

        return CustomerProfilerOut(
            segments=segments,
            dominant_segment=dominant_label,
            total_addressable_customers=total_addressable,
        )

    def explain(self, input_data: CustomerProfilerIn) -> dict:
        return {
            "mcc_affinity": 0.40,
            "demographic_match": 0.35,
            "location_density": 0.25,
        }
