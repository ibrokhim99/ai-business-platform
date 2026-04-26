from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_j import AMLPatternIn, AMLPatternOut


@register_model("M-J3")
class AMLPatternModel(BaseMLModel[AMLPatternIn, AMLPatternOut]):
    """
    Rule-based AML typology detector covering structuring, layering, and integration.
    Output: probability that the customer activity matches a money-laundering pattern,
    along with the dominant typology and SAR filing recommendation.
    """

    metadata = ModelMetadata(
        model_id="M-J3", block="J",
        name="AML Suspicious Pattern Detection",
        version="1.0.0",
        algorithm="Rule-based typology scorer (FATF structuring/layering heuristics)",
        is_stub=False,
        feature_names=["near_threshold_density", "rapid_in_out_ratio",
                       "counterparty_breadth", "cross_border_intensity",
                       "high_risk_jurisdiction"],
        supported_explainers=["rule_based"],
        description="Detects structuring, layering, and integration patterns; recommends SAR filings.",
    )

    def predict(self, input_data: AMLPatternIn) -> AMLPatternOut:
        threshold = input_data.structuring_threshold

        # ── Structuring score: many cash deposits sized just below the reporting threshold
        structuring = 0.0
        if input_data.cash_deposits_last_7d > 0:
            avg_deposit = input_data.cash_amount_last_7d / max(input_data.cash_deposits_last_7d, 1)
            near_density = input_data.near_threshold_deposits_30d / max(
                input_data.cash_deposits_last_7d * 4 + 1, 1)
            structuring = min(0.95, 0.20 * near_density + 0.30 * (
                avg_deposit / threshold if avg_deposit < threshold else 0))
            if input_data.near_threshold_deposits_30d >= 5:
                structuring = max(structuring, 0.65)

        # ── Layering score: rapid in/out cycles + many counterparties
        layering = 0.0
        if input_data.rapid_in_out_count_30d > 0:
            cp_breadth = min(input_data.distinct_counterparties_30d / 30.0, 1.0)
            io_intensity = min(input_data.rapid_in_out_count_30d / 20.0, 1.0)
            layering = 0.55 * io_intensity + 0.35 * cp_breadth
            layering = min(layering, 0.95)

        # ── Integration score: cross-border activity, especially to high-risk jurisdictions
        integration = 0.0
        if input_data.cross_border_count_30d > 0:
            cross_intensity = min(input_data.cross_border_count_30d / 15.0, 1.0)
            hr_factor = min(input_data.high_risk_jurisdiction_count / 5.0, 1.0)
            integration = 0.40 * cross_intensity + 0.55 * hr_factor
            integration = min(integration, 0.95)

        scores = {
            "structuring": round(structuring, 3),
            "layering": round(layering, 3),
            "integration": round(integration, 3),
        }
        dominant = max(scores, key=scores.get)
        suspicion = round(max(scores.values()), 3)

        triggered: list[str] = []
        if structuring >= 0.40:
            triggered.append("structuring")
        if layering >= 0.40:
            triggered.append("layering")
        if integration >= 0.40:
            triggered.append("integration")

        # Confidence ~ how cleanly one typology dominates
        ranked = sorted(scores.values(), reverse=True)
        confidence = round(min(1.0, ranked[0] - ranked[1] + 0.5), 3) if len(ranked) > 1 else 0.5

        if not triggered:
            typology = "none"
            sar = False
        else:
            typology = dominant
            sar = suspicion >= 0.55

        return AMLPatternOut(
            suspicion_score=suspicion,
            typology=typology,
            sar_recommended=sar,
            triggered_typologies=triggered,
            confidence=confidence,
        )

    def explain(self, input_data: AMLPatternIn) -> dict:
        return {
            "structuring_signals": 0.40,
            "layering_signals": 0.30,
            "cross_border_intensity": 0.20,
            "high_risk_jurisdiction": 0.10,
        }
