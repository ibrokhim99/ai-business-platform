import math

from scipy.stats import norm

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_i import InventoryOptimizerIn, InventoryOptimizerOut


@register_model("M-I1")
class InventoryOptimizerModel(BaseMLModel[InventoryOptimizerIn, InventoryOptimizerOut]):
    """
    EOQ + (s, S) policy with safety stock from a service-level z-score.

        EOQ            = sqrt(2 D K / h)
        Safety stock   = z * σ_LT
        Reorder point  = μ_LT + safety_stock
        Annual cost    = ordering + holding + safety holding
    """

    metadata = ModelMetadata(
        model_id="M-I1", block="I",
        name="Inventory Optimizer",
        version="1.0.0",
        algorithm="EOQ + (s, S) policy with normal-approximation safety stock",
        is_stub=False,
        feature_names=["annual_demand", "unit_cost", "ordering_cost",
                       "holding_cost_pct", "lead_time_days",
                       "demand_std_daily", "service_level"],
        supported_explainers=["rule_based"],
        description="Recommends EOQ, reorder point, and safety stock for a SKU.",
    )

    def predict(self, input_data: InventoryOptimizerIn) -> InventoryOptimizerOut:
        D = input_data.annual_demand
        K = input_data.ordering_cost
        h = input_data.holding_cost_pct * input_data.unit_cost   # $ per unit per year

        eoq = math.sqrt(2 * D * K / h) if h > 0 else 0.0

        daily_demand = D / 365.0
        mean_lt_demand = daily_demand * input_data.lead_time_days

        # Safety stock from a normal-approx demand-during-lead-time distribution
        z = norm.ppf(input_data.service_level)
        sigma_lt = input_data.demand_std_daily * math.sqrt(input_data.lead_time_days)
        safety = max(z * sigma_lt, 0.0)

        reorder_point = mean_lt_demand + safety
        annual_orders = D / eoq if eoq > 0 else 0.0

        annual_ordering = annual_orders * K
        annual_holding = (eoq / 2) * h
        annual_safety_holding = safety * h
        total_cost = annual_ordering + annual_holding + annual_safety_holding

        return InventoryOptimizerOut(
            economic_order_quantity=round(eoq, 2),
            reorder_point=round(reorder_point, 2),
            safety_stock=round(safety, 2),
            annual_orders=round(annual_orders, 2),
            total_annual_cost=round(total_cost, 2),
            target_service_level=input_data.service_level,
        )

    def explain(self, input_data: InventoryOptimizerIn) -> dict:
        return {
            "annual_demand": 0.40,
            "ordering_cost": 0.20,
            "holding_cost": 0.20,
            "lead_time": 0.10,
            "service_level": 0.10,
        }
