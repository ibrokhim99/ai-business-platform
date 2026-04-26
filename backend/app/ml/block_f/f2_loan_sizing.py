from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_f import LoanSizingIn, LoanSizingOut


def _monthly_payment(principal: float, monthly_rate: float, n: int) -> float:
    """Standard annuity payment formula."""
    if monthly_rate <= 0:
        return principal / n
    return principal * monthly_rate * (1 + monthly_rate) ** n / ((1 + monthly_rate) ** n - 1)


def _pv_annuity(monthly_payment: float, monthly_rate: float, n: int) -> float:
    """Present value of an annuity — maximum loan for a given payment."""
    if monthly_rate <= 0:
        return monthly_payment * n
    return monthly_payment * (1 - (1 + monthly_rate) ** -n) / monthly_rate


@register_model("M-F2")
class LoanSizingModel(BaseMLModel[LoanSizingIn, LoanSizingOut]):
    metadata = ModelMetadata(
        model_id="M-F2", block="F",
        name="Loan Sizing Recommender",
        version="1.0.0",
        algorithm="Annuity formula + 43% DTI constraint",
        is_stub=False,
        feature_names=["monthly_net_cashflow", "monthly_revenue", "existing_debt_monthly",
                       "loan_term_months", "interest_rate_annual_pct"],
        supported_explainers=["rule_based"],
        description="Optimal and maximum loan amount based on cash flow.",
    )

    def predict(self, input_data: LoanSizingIn) -> LoanSizingOut:
        monthly_rate = input_data.interest_rate_annual_pct / 100 / 12
        n = input_data.loan_term_months
        revenue = max(input_data.monthly_revenue, 1.0)

        # Maximum allowable total debt payment at 43% DTI
        max_total_payment = revenue * 0.43
        available_payment = max(max_total_payment - input_data.existing_debt_monthly, 0.0)

        # Maximum loan principal that produces `available_payment` per month
        max_loan = _pv_annuity(available_payment, monthly_rate, n)

        # Recommended: 80% of maximum (conservative buffer)
        recommended_loan = max_loan * 0.80

        # Actual monthly payment on recommended loan
        actual_payment = _monthly_payment(recommended_loan, monthly_rate, n)

        # DTI with recommended loan
        dti = (actual_payment + input_data.existing_debt_monthly) / revenue

        verdict = (
            "affordable" if dti <= 0.43
            else "tight" if dti <= 0.55
            else "unaffordable"
        )

        return LoanSizingOut(
            recommended_loan=round(recommended_loan, 2),
            max_loan=round(max_loan, 2),
            monthly_payment=round(actual_payment, 2),
            dti_ratio=round(dti, 4),
            affordability_verdict=verdict,
        )

    def explain(self, input_data: LoanSizingIn) -> dict:
        return {
            "cashflow_capacity": 0.50,
            "existing_debt_burden": 0.30,
            "interest_rate_effect": 0.20,
        }
