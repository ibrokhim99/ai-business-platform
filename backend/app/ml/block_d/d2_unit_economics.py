import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_d import UnitEconomicsIn, UnitEconomicsOut

# MCC-specific operating expense ratio (as % of gross margin consumed by operations)
# Net margin = gross_margin * (1 - opex_ratio)
_MCC_OPEX_RATIO: dict[str, float] = {
    "5812": 0.70,   # Restaurants: high labour + overhead
    "5814": 0.65,   # Fast food: slightly better
    "5411": 0.75,   # Grocery: thin margins
    "5912": 0.60,   # Pharmacy: moderate
    "7372": 0.45,   # Software: low opex
    "5045": 0.55,   # Electronics: moderate
    "5940": 0.65,   # Sporting goods
    "5999": 0.68,   # Misc retail
    "5661": 0.62,   # Shoe stores
    "5699": 0.63,   # Apparel
}
_DEFAULT_OPEX_RATIO = 0.65


def _ltv_cac_grade(ratio: float) -> str:
    if ratio >= 5.0:
        return "A"
    elif ratio >= 3.0:
        return "B"
    elif ratio >= 1.5:
        return "C"
    elif ratio >= 1.0:
        return "D"
    else:
        return "F"


@register_model("M-D2")
class UnitEconomicsModel(BaseMLModel[UnitEconomicsIn, UnitEconomicsOut]):
    metadata = ModelMetadata(
        model_id="M-D2",
        block="D",
        name="Unit Economics",
        version="1.0.0",
        algorithm="Cohort LTV model with MCC-adjusted operating expense ratios",
        is_stub=False,
        feature_names=["avg_transaction_value", "monthly_transactions", "customer_acquisition_cost",
                       "monthly_churn_rate_pct", "gross_margin_pct"],
        supported_explainers=["rule_based"],
        description="LTV, CAC, payback, and net margin using MCC-adjusted unit economics.",
    )

    def predict(self, input_data: UnitEconomicsIn) -> UnitEconomicsOut:
        churn_rate = input_data.monthly_churn_rate_pct / 100.0
        # Average customer lifetime in months
        avg_lifetime = 1.0 / churn_rate if churn_rate > 0 else 60.0

        # Monthly revenue per customer (assumes each customer does 1 transaction)
        monthly_rev_per_customer = input_data.avg_transaction_value

        # Monthly gross margin per customer
        gross_margin_per_customer = monthly_rev_per_customer * (input_data.gross_margin_pct / 100.0)

        # LTV = monthly gross margin per customer × average lifetime months
        ltv = gross_margin_per_customer * avg_lifetime

        cac = input_data.customer_acquisition_cost

        ltv_cac_ratio = round(ltv / cac, 3) if cac > 0 else float("inf")
        ltv_cac_ratio = float(np.clip(ltv_cac_ratio, 0, 9999))

        # Payback: months to recover CAC from monthly gross margin per customer
        payback_months = cac / gross_margin_per_customer if gross_margin_per_customer > 0 else float("inf")
        payback_months = float(np.clip(payback_months, 0, 999))

        # Net margin: apply MCC-specific opex ratio
        opex_ratio = _MCC_OPEX_RATIO.get(input_data.mcc_code, _DEFAULT_OPEX_RATIO)
        net_margin_pct = input_data.gross_margin_pct * (1.0 - opex_ratio)
        net_margin_pct = float(np.clip(net_margin_pct, -50, 50))

        grade = _ltv_cac_grade(ltv_cac_ratio)

        return UnitEconomicsOut(
            ltv=round(ltv, 2),
            cac=round(cac, 2),
            ltv_cac_ratio=round(ltv_cac_ratio, 3),
            payback_months=round(payback_months, 1),
            net_margin_pct=round(net_margin_pct, 1),
            unit_economics_grade=grade,
        )

    def explain(self, input_data: UnitEconomicsIn) -> dict:
        churn_rate = input_data.monthly_churn_rate_pct / 100.0
        avg_lifetime = 1.0 / churn_rate if churn_rate > 0 else 60.0
        opex_ratio = _MCC_OPEX_RATIO.get(input_data.mcc_code, _DEFAULT_OPEX_RATIO)
        return {
            "churn_rate_weight": 0.40,
            "gross_margin_weight": 0.35,
            "transaction_value_weight": 0.25,
            "avg_customer_lifetime_months": round(avg_lifetime, 1),
            "mcc_opex_ratio": opex_ratio,
            "effective_net_margin_factor": round(1.0 - opex_ratio, 3),
        }
