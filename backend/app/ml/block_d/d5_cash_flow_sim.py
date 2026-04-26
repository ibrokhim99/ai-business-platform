import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_d import CashFlowSimIn, CashFlowSimOut

_N_SIMULATIONS = 500

# Uzbekistan seasonal factors (Jan-Dec)
_SEASONALITY = np.array([
    0.88, 0.85, 1.10, 1.15, 1.05, 0.95,
    1.00, 0.98, 1.02, 1.12, 1.20, 1.30,
])

# MCC-specific revenue noise standard deviation (monthly)
_MCC_REVENUE_NOISE: dict[str, float] = {
    "5812": 0.12,   # Restaurants: moderate volatility
    "5814": 0.10,   # Fast food: lower
    "5411": 0.06,   # Grocery: stable
    "5912": 0.07,   # Pharmacy: stable
    "7372": 0.15,   # Software: higher project variance
    "5045": 0.14,   # Electronics: seasonal spikes
    "5940": 0.18,   # Sporting: high variance
    "5999": 0.12,   # Misc
}
_DEFAULT_NOISE = 0.10


@register_model("M-D5")
class CashFlowSimModel(BaseMLModel[CashFlowSimIn, CashFlowSimOut]):
    metadata = ModelMetadata(
        model_id="M-D5",
        block="D",
        name="Cash Flow Simulator",
        version="1.0.0",
        algorithm="Monte Carlo simulation (500 runs) with seasonal adjustment",
        is_stub=False,
        feature_names=["initial_investment", "monthly_revenue_base", "monthly_fixed_costs",
                       "cogs_pct", "growth_rate_monthly_pct"],
        supported_explainers=["rule_based"],
        description="Monte Carlo cash flow simulation with seasonality and stochastic revenue.",
    )

    def predict(self, input_data: CashFlowSimIn) -> CashFlowSimOut:
        seed = int(
            abs(input_data.monthly_revenue_base * 1.3 + input_data.initial_investment * 0.7)
        ) % (2**31)
        rng = np.random.default_rng(seed)

        n = input_data.horizon_months
        noise_std = _MCC_REVENUE_NOISE.get(input_data.mcc_code, _DEFAULT_NOISE)

        # Run Monte Carlo: collect cumulative cash flows for each simulation
        all_cumulative = np.zeros((n,), dtype=float)
        all_revenues = np.zeros((n,), dtype=float)
        all_costs = np.zeros((n,), dtype=float)

        for _ in range(_N_SIMULATIONS):
            cumulative = -input_data.initial_investment
            for m_idx in range(n):
                m = m_idx + 1
                season = float(_SEASONALITY[(m - 1) % 12])
                growth = (1 + input_data.growth_rate_monthly_pct / 100) ** m
                noise = rng.normal(1.0, noise_std)
                revenue = input_data.monthly_revenue_base * growth * season * noise
                revenue = max(revenue, 0.0)
                cogs = revenue * input_data.cogs_pct / 100
                costs = cogs + input_data.monthly_fixed_costs
                net = revenue - costs
                cumulative += net
                all_revenues[m_idx] += revenue
                all_costs[m_idx] += costs
                all_cumulative[m_idx] += cumulative

        # Compute P50 (median) scenario from averages
        monthly_cashflows = []
        cumulative_p50 = -input_data.initial_investment
        break_even_month = None
        cash_gap_months = []

        for m_idx in range(n):
            m = m_idx + 1
            rev_p50 = all_revenues[m_idx] / _N_SIMULATIONS
            cost_p50 = all_costs[m_idx] / _N_SIMULATIONS
            net_p50 = rev_p50 - cost_p50
            cumulative_p50 += net_p50

            if break_even_month is None and cumulative_p50 >= 0:
                break_even_month = m
            if cumulative_p50 < 0:
                cash_gap_months.append(m)

            monthly_cashflows.append({
                "month": m,
                "revenue": round(rev_p50, 2),
                "costs": round(cost_p50, 2),
                "net_cashflow": round(net_p50, 2),
                "cumulative": round(cumulative_p50, 2),
            })

        total_net = sum(cf["net_cashflow"] for cf in monthly_cashflows)

        return CashFlowSimOut(
            monthly_cashflows=monthly_cashflows,
            total_net=round(total_net, 2),
            cash_gap_months=cash_gap_months,
            break_even_month=break_even_month,
            final_balance=round(cumulative_p50, 2),
        )

    def explain(self, input_data: CashFlowSimIn) -> dict:
        noise_std = _MCC_REVENUE_NOISE.get(input_data.mcc_code, _DEFAULT_NOISE)
        return {
            "revenue_base_weight": 0.40,
            "cogs_pct_weight": 0.25,
            "fixed_costs_weight": 0.20,
            "seasonality_weight": 0.10,
            "growth_rate_weight": 0.05,
            "mcc_revenue_noise_std": noise_std,
            "n_simulations": _N_SIMULATIONS,
        }
