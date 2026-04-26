from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_e import EntryBarrierIn, EntryBarrierOut

# MCC regulatory scores (0–1): higher = more bureaucratic / regulated
_MCC_REG_SCORE = {
    "5812": 0.70,   # food service: health + fire + cash register
    "5813": 0.90,   # alcohol: license + age verification
    "5912": 0.95,   # pharmacy: MOH license + cold chain
    "5047": 0.80,   # medical equipment
    "7011": 0.65,   # hospitality
    "5411": 0.60,   # grocery
    "5651": 0.35,   # apparel
    "7372": 0.25,   # software services
    "5940": 0.30,   # sports goods
}
_DEFAULT_REG_SCORE = 0.45


@register_model("M-E4")
class EntryBarrierModel(BaseMLModel[EntryBarrierIn, EntryBarrierOut]):
    metadata = ModelMetadata(
        model_id="M-E4", block="E",
        name="Market Entry Barrier Index",
        version="1.0.0",
        algorithm="Composite index — capital + regulatory + brand + scale + switching",
        is_stub=False,
        feature_names=["mcc_code", "region_id", "initial_investment"],
        supported_explainers=["rule_based"],
        description="Height of market entry barriers 0–100.",
    )

    def predict(self, input_data: EntryBarrierIn) -> EntryBarrierOut:
        # Capital component: 0–40 points (investment ≥ $100k → full 40)
        capital_score = round(min(input_data.initial_investment / 100_000, 1.0) * 40, 1)

        # Regulatory component: 0–30 points
        reg_coef = _MCC_REG_SCORE.get(input_data.mcc_code, _DEFAULT_REG_SCORE)
        regulatory_score = round(reg_coef * 30, 1)

        # Brand loyalty: 0–15 points — higher for food/pharma
        brand_map = {
            "5812": 12, "5411": 14, "5912": 13, "5813": 11, "7011": 10,
        }
        brand_score = float(brand_map.get(input_data.mcc_code, 8))

        # Economies of scale: 0–10 points
        scale_map = {
            "5411": 9, "5812": 7, "5912": 8, "5813": 8,
        }
        scale_score = float(scale_map.get(input_data.mcc_code, 5))

        # Switching costs: 0–5 points
        switching_map = {
            "5912": 5, "7011": 4, "7372": 4, "5047": 4,
        }
        switching_score = float(switching_map.get(input_data.mcc_code, 2))

        total = round(capital_score + regulatory_score + brand_score + scale_score + switching_score, 1)
        total = min(total, 100.0)

        level = (
            "very_high" if total >= 75
            else "high" if total >= 55
            else "medium" if total >= 35
            else "low"
        )

        if capital_score >= 30:
            rec = (f"Barrier level: {level}. "
                   f"High capital requirement (≥$100k) is the primary constraint. "
                   f"Regulatory compliance adds {regulatory_score} pts.")
        elif regulatory_score >= 20:
            rec = (f"Barrier level: {level}. "
                   f"Regulatory complexity is the primary barrier — budget for licensing and compliance.")
        else:
            rec = (f"Barrier level: {level}. "
                   f"Market is relatively accessible. Focus on brand differentiation to build loyalty.")

        return EntryBarrierOut(
            barrier_index=total,
            barrier_level=level,
            components={
                "capital_requirement": capital_score,
                "regulatory": regulatory_score,
                "brand_loyalty": brand_score,
                "economies_of_scale": scale_score,
                "switching_costs": switching_score,
            },
            recommendation=rec,
        )

    def explain(self, input_data: EntryBarrierIn) -> dict:
        return {
            "capital": 0.40,
            "regulatory": 0.30,
            "brand_loyalty": 0.15,
            "economies_of_scale": 0.10,
            "switching_costs": 0.05,
        }
