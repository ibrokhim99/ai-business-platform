import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_d import ViabilityCheckIn, ViabilityCheckOut

_N_SIMULATIONS = 500

# Perturbation bounds for Monte Carlo
_REV_SHOCK_LOW = -0.20    # revenue can drop 20%
_REV_SHOCK_HIGH = 0.30    # revenue can rise 30%
_COST_SHOCK_STD = 0.15    # costs ±15%

# MCC-specific base survival adjustments (some sectors are inherently riskier)
_MCC_SURVIVAL_PRIOR: dict[str, float] = {
    "5812": -0.05,   # Restaurants: -5% base (high failure rate)
    "5814": -0.03,   # Fast food: slightly better
    "5411": +0.03,   # Grocery: staple good
    "5912": +0.05,   # Pharmacy: essential
    "7372": +0.08,   # Software: lower fixed costs
    "5940": -0.04,   # Sporting: discretionary
    "5999": -0.02,   # Misc retail: moderate
}
_DEFAULT_PRIOR = 0.0

# Seasonality for simulation (12-month pattern)
_SEASONALITY = np.array([
    0.88, 0.85, 1.10, 1.15, 1.05, 0.95,
    1.00, 0.98, 1.02, 1.12, 1.20, 1.30,
])


@register_model("M-D1")
class ViabilityCheckModel(BaseMLModel[ViabilityCheckIn, ViabilityCheckOut]):
    metadata = ModelMetadata(
        model_id="M-D1",
        block="D",
        name="Viability Check",
        version="1.0.0",
        algorithm="Monte Carlo simulation (500 runs) with revenue/cost perturbation",
        is_stub=False,
        feature_names=["monthly_revenue_estimate", "monthly_fixed_costs", "initial_investment", "monthly_rent"],
        supported_explainers=["rule_based"],
        description="2-year survival probability via Monte Carlo financial simulation.",
    )

    def predict(self, input_data: ViabilityCheckIn) -> ViabilityCheckOut:
        # Reproducible seed derived from input values
        seed = int(
            abs(input_data.monthly_revenue_estimate * 0.7 + input_data.initial_investment * 0.3)
        ) % (2**31)
        rng = np.random.default_rng(seed)

        n_months = 24
        n_sims = _N_SIMULATIONS

        # Monte Carlo: simulate n_sims trajectories of 24 months
        # Revenue perturbation: uniform between _REV_SHOCK_LOW and _REV_SHOCK_HIGH per run
        rev_shocks = rng.uniform(_REV_SHOCK_LOW, _REV_SHOCK_HIGH, n_sims)

        # Cost perturbation: normal ±_COST_SHOCK_STD per run
        cost_shocks = rng.normal(0, _COST_SHOCK_STD, n_sims)

        survival_count = 0
        for i in range(n_sims):
            cumulative = -input_data.initial_investment
            for m in range(1, n_months + 1):
                season = _SEASONALITY[(m - 1) % 12]
                monthly_noise = rng.normal(1.0, 0.05)  # month-to-month noise
                revenue = input_data.monthly_revenue_estimate * (1 + rev_shocks[i]) * season * monthly_noise
                costs = (input_data.monthly_fixed_costs + input_data.monthly_rent) * (1 + cost_shocks[i])
                cumulative += revenue - costs
            if cumulative > 0:
                survival_count += 1

        survival_prob = survival_count / n_sims

        # Apply MCC-specific prior adjustment
        prior_adj = _MCC_SURVIVAL_PRIOR.get(input_data.mcc_code, _DEFAULT_PRIOR)
        survival_prob = float(np.clip(survival_prob + prior_adj, 0.03, 0.97))

        # Deterministic risk identification
        monthly_costs = input_data.monthly_fixed_costs + input_data.monthly_rent
        base_net = input_data.monthly_revenue_estimate - monthly_costs
        rent_ratio = input_data.monthly_rent / max(input_data.monthly_revenue_estimate, 1.0)
        payback_months = input_data.initial_investment / max(base_net, 0.01) if base_net > 0 else None

        key_risks = []
        if rent_ratio > 0.30:
            key_risks.append(f"High rental burden: {rent_ratio*100:.1f}% of revenue (threshold: 30%)")
        if base_net < 0:
            key_risks.append(f"Negative base cash flow: {base_net:,.0f} USD/month")
        if payback_months and payback_months > 30:
            key_risks.append(f"Long payback period: {payback_months:.0f} months")
        if input_data.monthly_revenue_estimate < monthly_costs * 1.2:
            key_risks.append("Revenue margin below 20% buffer over total costs")
        if survival_prob < 0.5:
            key_risks.append("Monte Carlo indicates majority of scenarios result in failure")

        if survival_prob > 0.65:
            verdict = "viable"
        elif survival_prob > 0.45:
            verdict = "marginal"
        else:
            verdict = "high_risk"

        return ViabilityCheckOut(
            survival_probability_2y=round(survival_prob, 3),
            verdict=verdict,
            key_risks=key_risks,
            monthly_break_even=round(monthly_costs, 2),
            months_to_break_even=round(payback_months, 1) if payback_months else None,
        )

    def explain(self, input_data: ViabilityCheckIn) -> dict:
        monthly_costs = input_data.monthly_fixed_costs + input_data.monthly_rent
        base_net = input_data.monthly_revenue_estimate - monthly_costs
        return {
            "cash_flow_margin_weight": 0.50,
            "rental_burden_weight": 0.30,
            "investment_payback_weight": 0.20,
            "base_monthly_net": round(base_net, 2),
            "rent_to_revenue_pct": round(
                input_data.monthly_rent / max(input_data.monthly_revenue_estimate, 1) * 100, 2
            ),
            "n_simulations": _N_SIMULATIONS,
        }
