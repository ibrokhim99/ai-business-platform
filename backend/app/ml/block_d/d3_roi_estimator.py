import numpy as np
from scipy.optimize import brentq

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_d import ROIEstimatorIn, ROIEstimatorOut


def _npv(monthly_cashflows: list[float], initial_investment: float, monthly_rate: float) -> float:
    """Compute Net Present Value."""
    pv = 0.0
    for t, cf in enumerate(monthly_cashflows, start=1):
        pv += cf / ((1 + monthly_rate) ** t)
    return pv - initial_investment


def _compute_irr(monthly_cashflows: list[float], initial_investment: float) -> float | None:
    """Compute IRR as annual rate using scipy.optimize.brentq on NPV = 0."""
    def npv_at_rate(r: float) -> float:
        return _npv(monthly_cashflows, initial_investment, r)

    # Search for monthly rate where NPV = 0
    try:
        # Check if NPV changes sign in [near-zero, 100% monthly]
        low, high = 1e-8, 5.0  # monthly rate bounds
        if npv_at_rate(low) * npv_at_rate(high) > 0:
            return None  # No sign change → no real IRR in range
        monthly_irr = brentq(npv_at_rate, low, high, xtol=1e-6, maxiter=200)
        annual_irr = (1 + monthly_irr) ** 12 - 1
        return float(annual_irr * 100)
    except (ValueError, RuntimeError):
        return None


def _compute_payback(monthly_cashflows: list[float], initial_investment: float) -> float | None:
    """Compute payback period in months (fractional)."""
    cumulative = -initial_investment
    for m, cf in enumerate(monthly_cashflows, start=1):
        cumulative += cf
        if cumulative >= 0:
            # Interpolate within the month
            prev = cumulative - cf
            fraction = -prev / cf if cf > 0 else 0
            return m - 1 + fraction
    return None  # Never breaks even in the horizon


@register_model("M-D3")
class ROIEstimatorModel(BaseMLModel[ROIEstimatorIn, ROIEstimatorOut]):
    metadata = ModelMetadata(
        model_id="M-D3",
        block="D",
        name="ROI Estimator",
        version="1.0.0",
        algorithm="DCF: NPV + IRR via scipy.optimize.brentq",
        is_stub=False,
        feature_names=["initial_investment", "monthly_net_cash_flow", "discount_rate_annual_pct"],
        supported_explainers=["rule_based"],
        description="NPV, IRR (via brentq), payback, and ROI using full DCF methodology.",
    )

    def predict(self, input_data: ROIEstimatorIn) -> ROIEstimatorOut:
        monthly_rate = input_data.discount_rate_annual_pct / 100.0 / 12.0
        n_months = input_data.horizon_years * 12
        cashflows = [float(input_data.monthly_net_cash_flow)] * n_months

        # NPV
        npv = _npv(cashflows, input_data.initial_investment, monthly_rate)

        # IRR (annual %)
        irr_pct = None
        if input_data.monthly_net_cash_flow > 0:
            irr_pct = _compute_irr(cashflows, input_data.initial_investment)
            if irr_pct is not None:
                irr_pct = round(irr_pct, 2)

        # Payback period
        payback_months = _compute_payback(cashflows, input_data.initial_investment)
        if payback_months is not None:
            payback_months = round(float(payback_months), 1)

        # Simple ROI (undiscounted)
        total_cash = input_data.monthly_net_cash_flow * n_months
        roi_pct = (total_cash - input_data.initial_investment) / max(input_data.initial_investment, 1.0) * 100

        # Verdict
        if npv > 0 and (irr_pct is None or irr_pct > input_data.discount_rate_annual_pct):
            verdict = "profitable"
        elif npv > -input_data.initial_investment * 0.10:
            verdict = "marginal"
        else:
            verdict = "unprofitable"

        return ROIEstimatorOut(
            npv=round(float(npv), 2),
            irr_pct=irr_pct,
            payback_months=payback_months,
            roi_pct=round(float(roi_pct), 2),
            verdict=verdict,
        )

    def explain(self, input_data: ROIEstimatorIn) -> dict:
        monthly_rate = input_data.discount_rate_annual_pct / 100.0 / 12.0
        n_months = input_data.horizon_years * 12
        undiscounted_total = input_data.monthly_net_cash_flow * n_months
        discount_effect = undiscounted_total - sum(
            input_data.monthly_net_cash_flow / ((1 + monthly_rate) ** t)
            for t in range(1, n_months + 1)
        )
        return {
            "cashflow_magnitude_weight": 0.50,
            "discount_rate_weight": 0.30,
            "horizon_weight": 0.20,
            "undiscounted_total_cashflow": round(undiscounted_total, 2),
            "discount_effect_usd": round(float(discount_effect), 2),
            "monthly_discount_rate": round(monthly_rate, 6),
            "algorithm": "scipy.optimize.brentq",
        }
