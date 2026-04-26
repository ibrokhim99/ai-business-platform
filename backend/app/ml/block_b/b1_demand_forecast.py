import datetime

import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_b import DemandForecastIn, DemandForecastOut

# MCC-specific trend biases (monthly growth rate adjustments)
_MCC_TREND_BIAS: dict[str, float] = {
    "5812": 0.010,   # Restaurants: moderate growth
    "5814": 0.012,   # Fast food: higher growth
    "5411": 0.007,   # Grocery: stable growth
    "5912": 0.008,   # Pharmacy: steady
    "7372": 0.018,   # Software: fast growth
    "5045": 0.015,   # Electronics: fast
    "5940": 0.003,   # Sporting: slow
    "5999": 0.005,   # Misc retail: slow
}
_DEFAULT_TREND_BIAS = 0.008

# Uzbekistan seasonal factors (1.0 = baseline)
_SEASONAL_FACTORS = [
    0.88, 0.85, 1.10, 1.15, 1.05, 0.95,
    1.00, 0.98, 1.02, 1.12, 1.20, 1.30,
]


def _generate_history(base_revenue: float, trend_rate: float, seed: int, n_months: int = 24) -> np.ndarray:
    """Generate synthetic historical revenue series with trend, seasonality, and noise."""
    rng = np.random.default_rng(seed)
    months = np.arange(n_months)
    trend = base_revenue * (1 + trend_rate) ** months
    season = np.array([_SEASONAL_FACTORS[m % 12] for m in months])
    noise = rng.normal(1.0, 0.05, n_months)
    return trend * season * noise


@register_model("M-B1")
class DemandForecastModel(BaseMLModel[DemandForecastIn, DemandForecastOut]):
    metadata = ModelMetadata(
        model_id="M-B1",
        block="B",
        name="Demand Forecasting (12/24/36 months)",
        version="1.0.0",
        algorithm="Holt-Winters ExponentialSmoothing with MCC trend bias",
        is_stub=False,
        feature_names=["region_id", "mcc_code", "base_monthly_revenue"],
        supported_explainers=["rule_based"],
        description="Forecasts niche revenue using Holt-Winters ExponentialSmoothing.",
    )

    def predict(self, input_data: DemandForecastIn) -> DemandForecastOut:
        trend_rate = _MCC_TREND_BIAS.get(input_data.mcc_code, _DEFAULT_TREND_BIAS)

        # Reproducible seed from region + mcc
        seed = hash(f"{input_data.region_id}_{input_data.mcc_code}") % (2**31)
        history = _generate_history(input_data.base_monthly_revenue, trend_rate, seed)

        # Fit Holt-Winters with additive seasonality (period=12)
        model = ExponentialSmoothing(
            history,
            trend="add",
            seasonal="add",
            seasonal_periods=12,
            initialization_method="estimated",
        )
        fit = model.fit(optimized=True)

        # Forecast horizon_months ahead
        fc_values = fit.forecast(input_data.horizon_months)

        # Compute residual std for prediction intervals
        resid_std = float(np.std(fit.resid))
        z_90 = 1.645  # 90% prediction interval

        forecast = []
        for i, fc in enumerate(fc_values):
            m = i + 1
            predicted = float(max(fc, 0.0))
            margin = z_90 * resid_std * np.sqrt(m)  # growing uncertainty
            lower = max(predicted - margin, 0.0)
            upper = predicted + margin
            forecast.append({
                "month": m,
                "predicted": round(float(predicted), 2),
                "lower": round(float(lower), 2),
                "upper": round(float(upper), 2),
            })

        # Compute CAGR from forecast
        if len(fc_values) >= 12:
            cagr = ((fc_values[11] / max(history[-1], 0.01)) - 1) * 100
        else:
            cagr = trend_rate * 12 * 100

        # Determine overall trend
        slope = float(np.polyfit(range(len(fc_values)), fc_values, 1)[0])
        if slope > input_data.base_monthly_revenue * 0.005:
            trend = "growing"
        elif slope < -input_data.base_monthly_revenue * 0.005:
            trend = "declining"
        else:
            trend = "stable"

        return DemandForecastOut(
            forecast=forecast,
            trend=trend,
            cagr_pct=round(float(cagr), 2),
            model_used="ExponentialSmoothing",
        )

    def explain(self, input_data: DemandForecastIn) -> dict:
        trend_rate = _MCC_TREND_BIAS.get(input_data.mcc_code, _DEFAULT_TREND_BIAS)
        return {
            "base_revenue_weight": 0.55,
            "trend_weight": 0.30,
            "seasonality_weight": 0.15,
            "mcc_trend_bias": trend_rate,
            "model": "HoltWinters_ExponentialSmoothing",
        }
