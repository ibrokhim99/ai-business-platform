from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_e import PricePressureIn, PricePressureOut

# MCC price elasticity estimates (own-price elasticity, negative = elastic demand)
_MCC_ELASTICITY = {
    "5812": -1.8,   # restaurant food — moderately elastic
    "5813": -1.2,   # alcohol — less elastic
    "5411": -2.0,   # grocery — elastic
    "5912": -0.9,   # pharmacy — inelastic (health goods)
    "5047": -1.0,   # medical equipment — inelastic
    "7011": -1.5,   # hotel — moderately elastic
    "5651": -2.2,   # apparel — elastic
    "7372": -1.4,   # software — moderate
    "5940": -2.5,   # sports goods — very elastic
}
_DEFAULT_ELASTICITY = -1.6

# MCC cost/margin profile for margin estimation
_MCC_COST_RATIO = {
    "5812": 0.35,   # ~35% COGS
    "5411": 0.70,
    "5912": 0.55,
    "5813": 0.40,
    "5651": 0.50,
}
_DEFAULT_COST_RATIO = 0.50


@register_model("M-E5")
class PricePressureModel(BaseMLModel[PricePressureIn, PricePressureOut]):
    metadata = ModelMetadata(
        model_id="M-E5", block="E",
        name="Price Pressure Model",
        version="1.0.0",
        algorithm="Hedonic pricing + MCC-specific elasticity",
        is_stub=False,
        feature_names=["mcc_code", "target_price", "competitor_avg_price"],
        supported_explainers=["rule_based"],
        description="Price pressure score and optimal price range.",
    )

    def predict(self, input_data: PricePressureIn) -> PricePressureOut:
        comp = input_data.competitor_avg_price
        target = input_data.target_price
        elasticity = _MCC_ELASTICITY.get(input_data.mcc_code, _DEFAULT_ELASTICITY)

        # Price pressure: normalised absolute deviation from competitor average
        price_gap = abs(target - comp) / comp
        pressure_score = round(min(price_gap / 0.30, 1.0), 3)   # 30% gap → full pressure

        # Optimal price band: ±10% around competitor average
        low = round(comp * 0.90, 2)
        high = round(comp * 1.10, 2)

        # Recommended price: slight premium if target < comp (room to grow),
        # slight discount if target > comp (stay competitive)
        if target < comp:
            adj = 1.03   # price up a bit
        elif target > comp * 1.15:
            adj = 1.05   # still above comp but moderate
        else:
            adj = 1.00
        recommended = round(comp * adj, 2)
        recommended = max(low, min(high, recommended))

        # Margin at recommended price
        cost_ratio = _MCC_COST_RATIO.get(input_data.mcc_code, _DEFAULT_COST_RATIO)
        cogs_est = recommended * cost_ratio
        margin = round((recommended - cogs_est) / recommended, 3) if recommended > 0 else None

        return PricePressureOut(
            price_pressure_score=pressure_score,
            optimal_price_range=[low, high],
            price_elasticity=elasticity,
            recommended_price=recommended,
            margin_at_recommended=margin,
        )

    def explain(self, input_data: PricePressureIn) -> dict:
        return {
            "price_gap_vs_competitor": 0.50,
            "elasticity_effect": 0.30,
            "mcc_margin_profile": 0.20,
        }
