import numpy as np
from statsmodels.tsa.ar_model import AutoReg

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_b import BusinessRegistrationIn, BusinessRegistrationOut

# MCC-specific base registration rates (new businesses per month per 100k population proxy)
_MCC_BASE_REGISTRATIONS: dict[str, float] = {
    "5812": 12.0,   # Restaurants: high entry rate
    "5814": 10.0,   # Fast food: high
    "5411": 6.0,    # Grocery: moderate
    "5912": 4.0,    # Pharmacy: lower (regulatory barriers)
    "7372": 8.0,    # Software: moderate
    "5045": 5.0,    # Electronics: moderate
    "5940": 3.0,    # Sporting: lower
    "5999": 7.0,    # Misc retail: moderate
    "5661": 5.0,    # Shoe stores: moderate
    "5699": 6.0,    # Apparel: moderate
}
_DEFAULT_BASE = 7.0

# MCC-specific annual growth in registrations
_MCC_REG_GROWTH: dict[str, float] = {
    "5812": 0.12,
    "5814": 0.15,
    "5411": 0.06,
    "5912": 0.04,
    "7372": 0.20,
    "5045": 0.14,
    "5940": 0.02,
    "5999": 0.05,
}
_DEFAULT_REG_GROWTH = 0.08

# Competition intensity thresholds (annual_growth_pct → label)
def _competition_intensity(annual_growth_pct: float) -> str:
    if annual_growth_pct >= 15.0:
        return "very_high"
    elif annual_growth_pct >= 10.0:
        return "high"
    elif annual_growth_pct >= 5.0:
        return "medium"
    else:
        return "low"


def _generate_registration_history(mcc_code: str, region_id: str, n: int = 36) -> np.ndarray:
    """Generate synthetic monthly registration counts for AutoReg fitting."""
    base = _MCC_BASE_REGISTRATIONS.get(mcc_code, _DEFAULT_BASE)
    annual_growth = _MCC_REG_GROWTH.get(mcc_code, _DEFAULT_REG_GROWTH)
    monthly_growth = annual_growth / 12

    seed = abs(hash(f"{mcc_code}_{region_id}_reg")) % (2**31)
    rng = np.random.default_rng(seed)

    months = np.arange(n)
    trend = base * (1 + monthly_growth) ** months
    # Poisson noise for count data
    history = rng.poisson(trend).astype(float)
    return np.maximum(history, 0)


@register_model("M-B6")
class BusinessRegistrationModel(BaseMLModel[BusinessRegistrationIn, BusinessRegistrationOut]):
    metadata = ModelMetadata(
        model_id="M-B6",
        block="B",
        name="Business Registration Forecast",
        version="1.0.0",
        algorithm="AutoReg(3) on synthetic Poisson registration series",
        is_stub=False,
        feature_names=["region_id", "mcc_code", "horizon_months"],
        supported_explainers=["rule_based"],
        description="Forecasts new competitor registrations using AutoRegressive model.",
    )

    def predict(self, input_data: BusinessRegistrationIn) -> BusinessRegistrationOut:
        annual_growth = _MCC_REG_GROWTH.get(input_data.mcc_code, _DEFAULT_REG_GROWTH)
        history = _generate_registration_history(
            input_data.mcc_code, input_data.region_id, n=36
        )

        # Fit AutoReg(3) on history
        try:
            model = AutoReg(history, lags=3, trend="ct")
            fit = model.fit()
            # Forecast h steps ahead
            start = len(history)
            end = len(history) + input_data.horizon_months - 1
            ar_forecast = fit.predict(start=start, end=end)
        except Exception:
            # Fallback: simple trend extrapolation
            monthly_growth = annual_growth / 12
            base = float(history[-1]) if len(history) > 0 else _DEFAULT_BASE
            ar_forecast = np.array([
                base * (1 + monthly_growth) ** m
                for m in range(1, input_data.horizon_months + 1)
            ])

        forecast = []
        cumulative = 0
        for m, fc in enumerate(ar_forecast, start=1):
            new_reg = max(int(round(float(fc))), 0)
            cumulative += new_reg
            forecast.append({
                "month": m,
                "new_registrations": new_reg,
                "cumulative": cumulative,
            })

        # Annual growth pct: extrapolate from first/last month if horizon < 12
        if len(forecast) >= 2:
            first_reg = forecast[0]["new_registrations"]
            last_reg = forecast[-1]["new_registrations"]
            n_months = len(forecast)
            if first_reg > 0:
                # Annualize the growth rate: (last/first)^(12/n) - 1
                monthly_rate = (last_reg / first_reg) ** (1.0 / n_months) - 1
                actual_annual_growth_pct = round(monthly_rate * 12 * 100, 1)
            else:
                actual_annual_growth_pct = round(annual_growth * 100, 1)
        else:
            actual_annual_growth_pct = round(annual_growth * 100, 1)

        return BusinessRegistrationOut(
            forecast=forecast,
            annual_growth_pct=actual_annual_growth_pct,
            competition_intensity=_competition_intensity(actual_annual_growth_pct),
        )

    def explain(self, input_data: BusinessRegistrationIn) -> dict:
        annual_growth = _MCC_REG_GROWTH.get(input_data.mcc_code, _DEFAULT_REG_GROWTH)
        base = _MCC_BASE_REGISTRATIONS.get(input_data.mcc_code, _DEFAULT_BASE)
        return {
            "market_growth_weight": 0.50,
            "barrier_to_entry_weight": 0.30,
            "regulatory_ease_weight": 0.20,
            "mcc_base_registrations_per_month": base,
            "mcc_annual_growth_rate": round(annual_growth, 4),
            "algorithm": "AutoReg(3)",
        }
