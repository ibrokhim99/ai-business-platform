from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_h import LTVCACRatioIn, LTVCACRatioOut


@register_model("M-H2")
class LTVCACRatioModel(BaseMLModel[LTVCACRatioIn, LTVCACRatioOut]):
    """
    Closed-form contractual LTV with discounting:
        LTV = (ARPU × margin) / (churn + monthly_discount)

    Standard SaaS-style formula; payback months = CAC / monthly contribution margin.
    """

    metadata = ModelMetadata(
        model_id="M-H2", block="H",
        name="LTV / CAC Ratio",
        version="1.0.0",
        algorithm="Closed-form contractual LTV with discount + payback period",
        is_stub=False,
        feature_names=["arpu_monthly", "gross_margin_pct",
                       "monthly_churn_rate", "discount_rate_annual", "cac"],
        supported_explainers=["rule_based"],
        description="LTV, payback months, and LTV/CAC verdict for unit economics review.",
    )

    def predict(self, input_data: LTVCACRatioIn) -> LTVCACRatioOut:
        monthly_discount = (1 + input_data.discount_rate_annual) ** (1 / 12) - 1
        contribution = input_data.arpu_monthly * input_data.gross_margin_pct
        ltv = contribution / (input_data.monthly_churn_rate + monthly_discount)
        ratio = ltv / input_data.cac

        # Payback (months) — undefined if contribution ≤ 0
        if contribution > 0:
            payback = input_data.cac / contribution
        else:
            payback = float("inf")

        if ratio < 1.0:
            verdict = "unsustainable"
            recs = [
                "CAC exceeds lifetime value — unit economics are negative",
                "Reduce CAC (target lower-cost channels) or increase ARPU/retention",
            ]
        elif ratio < 3.0:
            verdict = "marginal"
            recs = [
                "Ratio below the 3:1 SaaS benchmark",
                "Improve retention to extend lifetime",
                "Reassess channel mix to lower CAC",
            ]
        elif ratio < 5.0:
            verdict = "healthy"
            recs = [
                "Solid ratio — proceed with growth investment",
                "Watch payback period as you scale spend",
            ]
        else:
            verdict = "excellent"
            recs = [
                "Strong unit economics — opportunity to invest more aggressively",
                "Test higher-CAC, higher-LTV channels (e.g., enterprise)",
            ]

        return LTVCACRatioOut(
            ltv=round(ltv, 2),
            ltv_cac_ratio=round(ratio, 3),
            payback_months=round(payback, 2) if payback != float("inf") else 9_999.0,
            verdict=verdict,
            recommendations=recs,
        )

    def explain(self, input_data: LTVCACRatioIn) -> dict:
        return {
            "arpu": 0.30,
            "gross_margin": 0.25,
            "churn_rate": 0.30,
            "cac": 0.10,
            "discount_rate": 0.05,
        }
