import math

from scipy.stats import norm

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_i import StockoutRiskIn, StockoutRiskOut


@register_model("M-I2")
class StockoutRiskModel(BaseMLModel[StockoutRiskIn, StockoutRiskOut]):
    """
    Stockout probability over a planning horizon.

    Cumulative demand over (lead_time + horizon) days is approximated as
    Normal(μ × T, σ × √T). Stockout occurs when cumulative demand > available
    inventory (on_hand + on_order).
    """

    metadata = ModelMetadata(
        model_id="M-I2", block="I",
        name="Stockout Risk",
        version="1.0.0",
        algorithm="Normal-approx demand × lead-time tail probability",
        is_stub=False,
        feature_names=["on_hand_units", "on_order_units",
                       "daily_demand_mean", "daily_demand_std",
                       "lead_time_days_mean", "lead_time_days_std", "horizon_days"],
        supported_explainers=["rule_based"],
        description="Stockout probability and days-of-cover for a SKU over a horizon.",
    )

    def predict(self, input_data: StockoutRiskIn) -> StockoutRiskOut:
        T = input_data.horizon_days + input_data.lead_time_days_mean
        mu = input_data.daily_demand_mean * T
        # Combine demand variance and lead-time variance (independent contributions)
        var = (input_data.daily_demand_std ** 2 * T) + (
            input_data.daily_demand_mean ** 2 * input_data.lead_time_days_std ** 2)
        sigma = math.sqrt(max(var, 1e-9))

        available = input_data.on_hand_units + input_data.on_order_units
        # P(demand > available)
        prob = 1.0 - norm.cdf((available - mu) / sigma) if sigma > 0 else (
            1.0 if available < mu else 0.0)
        prob = float(round(min(max(prob, 0.001), 0.999), 4))

        # Expected days where on_hand exceeds zero before stockout
        days_of_cover = available / max(input_data.daily_demand_mean, 1e-6)

        # Expected stockout days = max(0, total demand - available) / daily mean
        deficit = max(mu - available, 0.0)
        expected_stockout_days = round(deficit / max(input_data.daily_demand_mean, 1e-6), 2)

        if prob < 0.05:
            level = "low"
            action = "No action required"
        elif prob < 0.20:
            level = "medium"
            action = "Place a replenishment order at next review cycle"
        elif prob < 0.50:
            level = "high"
            action = "Expedite reorder; consider partial shipment from alt supplier"
        else:
            level = "critical"
            action = "Emergency procurement; communicate ETAs to customers"

        return StockoutRiskOut(
            stockout_probability=prob,
            expected_stockout_days=expected_stockout_days,
            days_of_cover=round(days_of_cover, 2),
            risk_level=level,
            recommended_action=action,
        )

    def explain(self, input_data: StockoutRiskIn) -> dict:
        return {
            "available_inventory": 0.40,
            "demand_rate": 0.30,
            "demand_volatility": 0.15,
            "lead_time": 0.15,
        }
