from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_i import SupplierRiskIn, SupplierRiskOut


@register_model("M-I3")
class SupplierRiskModel(BaseMLModel[SupplierRiskIn, SupplierRiskOut]):
    """
    Weighted rule-based supplier risk scorer.
    Combines: delivery reliability, quality, payment behaviour, concentration,
    single-sourcing, and geopolitical exposure into a 0–1000 risk score.
    """

    metadata = ModelMetadata(
        model_id="M-I3", block="I",
        name="Supplier Risk Score",
        version="1.0.0",
        algorithm="Weighted multi-factor rule scorer",
        is_stub=False,
        feature_names=["months_active", "on_time_delivery_rate",
                       "quality_defect_rate", "payment_delay_avg_days",
                       "revenue_concentration_pct", "single_source_flag",
                       "geopolitical_risk"],
        supported_explainers=["rule_based"],
        description="0–1000 supplier risk score with band, primary driver, and contingency actions.",
    )

    def predict(self, input_data: SupplierRiskIn) -> SupplierRiskOut:
        # Component scores in [0, 1] — higher = riskier
        delivery_risk = 1.0 - input_data.on_time_delivery_rate
        quality_risk = min(input_data.quality_defect_rate * 10, 1.0)
        payment_risk = min(input_data.payment_delay_avg_days / 60.0, 1.0)
        tenure_risk = max(0.0, 1.0 - input_data.months_active / 36.0)
        concentration_risk = input_data.revenue_concentration_pct
        single_source_risk = 1.0 if input_data.single_source_flag else 0.0
        geo_risk = input_data.geopolitical_risk

        weights = {
            "delivery": 0.22,
            "quality": 0.18,
            "payment": 0.10,
            "tenure": 0.05,
            "concentration": 0.18,
            "single_source": 0.12,
            "geopolitical": 0.15,
        }

        components = {
            "delivery": delivery_risk,
            "quality": quality_risk,
            "payment": payment_risk,
            "tenure": tenure_risk,
            "concentration": concentration_risk,
            "single_source": single_source_risk,
            "geopolitical": geo_risk,
        }

        score = sum(weights[k] * v for k, v in components.items())
        score = max(0.0, min(score, 1.0))
        risk_score = round(score * 1000)

        primary_driver = max(
            components, key=lambda k: weights[k] * components[k]
        )

        if risk_score < 250:
            band = "low"
            actions = ["Maintain current relationship", "Annual review"]
        elif risk_score < 500:
            band = "medium"
            actions = [
                "Quarterly performance review",
                "Identify back-up supplier for top SKUs",
            ]
        elif risk_score < 750:
            band = "high"
            actions = [
                "Diversify sourcing — onboard a secondary supplier within 90 days",
                "Negotiate stricter SLAs",
                "Increase safety stock for affected SKUs",
            ]
        else:
            band = "severe"
            actions = [
                "Halt new POs pending replacement-supplier qualification",
                "Activate contingency stock",
                "Escalate to procurement governance committee",
            ]

        return SupplierRiskOut(
            risk_score=float(risk_score),
            risk_band=band,
            primary_risk_factor=primary_driver,
            contingency_actions=actions,
        )

    def explain(self, input_data: SupplierRiskIn) -> dict:
        return {
            "delivery_risk": 0.22,
            "quality_risk": 0.18,
            "concentration_risk": 0.18,
            "geopolitical_risk": 0.15,
            "single_source_risk": 0.12,
            "payment_risk": 0.10,
            "tenure_risk": 0.05,
        }
