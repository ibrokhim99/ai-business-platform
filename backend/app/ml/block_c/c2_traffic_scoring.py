import math

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_c import TrafficScoringIn, TrafficScoringOut

# ---------------------------------------------------------------------------
# Train GradientBoostingRegressor on synthetic GPS/time → traffic data
# Features: [lat_norm, lon_norm, hour_of_day, day_of_week]
# ---------------------------------------------------------------------------

def _build_traffic_model() -> tuple[GradientBoostingRegressor, GradientBoostingRegressor]:
    """Build and fit foot + auto traffic models on synthetic data."""
    rng = np.random.default_rng(seed=123)
    n = 2000

    # Synthetic GPS coords roughly around Central Asia (lat 37-43, lon 56-74)
    lat = rng.uniform(37, 43, n)
    lon = rng.uniform(56, 74, n)
    hour = rng.integers(0, 24, n).astype(float)
    dow = rng.integers(0, 7, n).astype(float)  # 0=Mon ... 6=Sun

    # Normalize features
    lat_norm = (lat - 37) / 6
    lon_norm = (lon - 56) / 18

    X = np.column_stack([lat_norm, lon_norm, hour / 23.0, dow / 6.0])

    # Synthetic foot traffic: peaks at hour 9-10 and 18-19, weekends higher
    base_foot = 500 + 3000 * (lat_norm * 0.6 + lon_norm * 0.4)
    hour_mult = (
        0.2 + 0.8 * np.exp(-((hour - 9.5) ** 2) / 8)
        + 0.6 * np.exp(-((hour - 18.5) ** 2) / 6)
    )
    weekend_mult = 1.0 + 0.3 * (dow >= 5).astype(float)
    noise_foot = rng.normal(1.0, 0.12, n)
    y_foot = base_foot * hour_mult * weekend_mult * noise_foot
    y_foot = np.clip(y_foot, 0, 15000)

    # Synthetic auto traffic: peaks at rush hours (8 and 17)
    base_auto = 300 + 2000 * (lat_norm * 0.5 + lon_norm * 0.5)
    auto_hour_mult = (
        0.15 + 0.9 * np.exp(-((hour - 8) ** 2) / 5)
        + 0.85 * np.exp(-((hour - 17) ** 2) / 5)
    )
    noise_auto = rng.normal(1.0, 0.15, n)
    y_auto = base_auto * auto_hour_mult * weekend_mult * noise_auto
    y_auto = np.clip(y_auto, 0, 10000)

    params = dict(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)
    model_foot = GradientBoostingRegressor(**params).fit(X, y_foot)
    model_auto = GradientBoostingRegressor(**params).fit(X, y_auto)
    return model_foot, model_auto


_MODEL_FOOT, _MODEL_AUTO = _build_traffic_model()

# Typical Uzbekistan hourly relative traffic profile (normalized)
_BASE_HOURLY = np.array([
    0.15, 0.08, 0.05, 0.04, 0.06, 0.20,
    0.55, 0.80, 0.95, 0.98, 0.92, 0.85,
    0.80, 0.78, 0.75, 0.80, 0.90, 1.00,
    0.95, 0.82, 0.70, 0.55, 0.38, 0.25,
])

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_WEEKEND_DAYS = ["Friday", "Saturday"]

# Seasonal factor (current month → multiplier based on Uzbekistan climate/events)
_MONTHLY_SEASONAL = [
    0.92, 0.90, 1.08, 1.12, 1.05, 0.96,
    1.00, 0.98, 1.02, 1.10, 1.18, 1.28,
]


@register_model("M-C2")
class TrafficScoringModel(BaseMLModel[TrafficScoringIn, TrafficScoringOut]):
    metadata = ModelMetadata(
        model_id="M-C2",
        block="C",
        name="Traffic Scoring",
        version="1.0.0",
        algorithm="GradientBoostingRegressor trained on synthetic GPS+time data",
        is_stub=False,
        feature_names=["lat", "lon", "radius_m"],
        supported_explainers=["shap_tree"],
        description="Foot and auto traffic estimation by hour, day, and season.",
    )

    def predict(self, input_data: TrafficScoringIn) -> TrafficScoringOut:
        lat_norm = (input_data.lat - 37) / 6
        lon_norm = (input_data.lon - 56) / 18

        # Average over all hours to get daily total
        daily_foot = 0.0
        daily_auto = 0.0
        hourly_raw = []
        for h in range(24):
            # Average over weekday (0-4) and weekend (5-6)
            foot_wday = 0.0
            auto_wday = 0.0
            for dow in range(7):
                X = np.array([[lat_norm, lon_norm, h / 23.0, dow / 6.0]])
                foot_wday += float(_MODEL_FOOT.predict(X)[0])
                auto_wday += float(_MODEL_AUTO.predict(X)[0])
            foot_h = foot_wday / 7
            auto_h = auto_wday / 7
            hourly_raw.append(foot_h)
            daily_foot += foot_h
            daily_auto += auto_h / 7

        # Scale by radius (traffic within radius proportional to area)
        area_factor = math.pi * (input_data.radius_m / 1000) ** 2
        scale = float(np.clip(area_factor * 0.5, 0.1, 10.0))

        daily_foot_int = int(daily_foot * scale)
        daily_auto_int = int(daily_auto * scale)

        # Normalize hourly profile to [0, 1]
        max_h = max(hourly_raw) if max(hourly_raw) > 0 else 1.0
        hourly_profile = [round(v / max_h, 3) for v in hourly_raw]

        # Peak hours: top 4 hours
        sorted_hours = sorted(range(24), key=lambda h: hourly_profile[h], reverse=True)
        peak_hours = sorted(sorted_hours[:4])

        # Seasonal factor: use current month (approximated as average)
        import datetime
        current_month = datetime.date.today().month
        seasonal_factor = float(_MONTHLY_SEASONAL[current_month - 1])

        return TrafficScoringOut(
            daily_foot_traffic=daily_foot_int,
            daily_auto_traffic=daily_auto_int,
            peak_hours=peak_hours,
            peak_days=_WEEKEND_DAYS,
            hourly_profile=hourly_profile,
            seasonal_factor=round(seasonal_factor, 2),
        )

    def explain(self, input_data: TrafficScoringIn) -> dict:
        importances_foot = _MODEL_FOOT.feature_importances_
        importances_auto = _MODEL_AUTO.feature_importances_
        feat_names = ["lat_norm", "lon_norm", "hour_of_day", "day_of_week"]
        return {
            "foot_traffic_feature_importances": {
                f: round(float(v), 4) for f, v in zip(feat_names, importances_foot)
            },
            "auto_traffic_feature_importances": {
                f: round(float(v), 4) for f, v in zip(feat_names, importances_auto)
            },
            "model_type": "GradientBoostingRegressor",
        }
