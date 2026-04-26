from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_f import DTIPredictorIn, DTIPredictorOut

# MCC sector monthly revenue growth rate
_MCC_GROWTH = {
    "5812": 0.010,   # restaurants: 1% / month
    "5411": 0.008,   # grocery: 0.8%
    "5912": 0.007,   # pharmacy: 0.7%
    "5651": 0.009,   # apparel: 0.9%
    "7011": 0.012,   # hotel: 1.2%
    "7372": 0.015,   # software: 1.5%
}
_DEFAULT_GROWTH = 0.008   # 0.8% monthly baseline


def _annuity_payment(principal: float, monthly_rate: float, n: int) -> float:
    if monthly_rate <= 0:
        return principal / n
    return principal * monthly_rate * (1 + monthly_rate) ** n / ((1 + monthly_rate) ** n - 1)


@register_model("M-F3")
class DTIPredictorModel(BaseMLModel[DTIPredictorIn, DTIPredictorOut]):
    metadata = ModelMetadata(
        model_id="M-F3", block="F",
        name="DTI Predictor",
        version="1.0.0",
        algorithm="Projected revenue growth + annuity payment formula",
        is_stub=False,
        feature_names=["mcc_code", "initial_monthly_revenue", "proposed_loan_amount",
                       "loan_term_months", "interest_rate_annual_pct"],
        supported_explainers=["rule_based"],
        description="Predicts debt-to-income at 6/12/24 months post-opening.",
    )

    def predict(self, input_data: DTIPredictorIn) -> DTIPredictorOut:
        monthly_rate = input_data.interest_rate_annual_pct / 100 / 12
        n = input_data.loan_term_months
        payment = _annuity_payment(input_data.proposed_loan_amount, monthly_rate, n)
        growth = _MCC_GROWTH.get(input_data.mcc_code, _DEFAULT_GROWTH)

        safe = 0.43
        checkpoints = [6, 12, 24]
        dti_map: dict[int, float] = {}

        for m in checkpoints:
            projected_revenue = input_data.initial_monthly_revenue * (1 + growth) ** m
            dti_map[m] = round(payment / max(projected_revenue, 1.0), 4)

        risk_periods = [m for m in checkpoints if dti_map[m] > safe]

        delta = dti_map[24] - dti_map[6]
        if delta < -0.02:
            trajectory = "improving"
        elif delta > 0.02:
            trajectory = "deteriorating"
        else:
            trajectory = "stable"

        return DTIPredictorOut(
            dti_at_6m=dti_map[6],
            dti_at_12m=dti_map[12],
            dti_at_24m=dti_map[24],
            safe_threshold=safe,
            risk_periods=risk_periods,
            trajectory=trajectory,
        )

    def explain(self, input_data: DTIPredictorIn) -> dict:
        return {
            "revenue_growth_rate": 0.40,
            "loan_payment_size": 0.40,
            "mcc_sector_growth": 0.20,
        }
