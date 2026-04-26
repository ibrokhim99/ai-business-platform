from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_h import OptimalPricingIn, OptimalPricingOut


@register_model("M-H5")
class OptimalPricingModel(BaseMLModel[OptimalPricingIn, OptimalPricingOut]):
    """
    Constant-elasticity (log-log) demand model:
        Q(p) = Q0 × (p / p0) ^ ε       where ε < 0

    Revenue-maximising price (no MC):  p* = ∞ if ε > -1 (inelastic — raise price)
                                       p* = current_price × (ε / (ε + 1))^(1/ε)  …always undefined cleanly
    Margin-maximising price (with MC): p* = MC × (ε / (ε + 1))   for ε < -1.
    """

    metadata = ModelMetadata(
        model_id="M-H5", block="H",
        name="Optimal Pricing",
        version="1.0.0",
        algorithm="Log-log price elasticity → margin-maximising price (Lerner condition)",
        is_stub=False,
        feature_names=["current_price", "current_units_sold",
                       "unit_cost", "elasticity_estimate"],
        supported_explainers=["rule_based"],
        description="Optimal price recommendation given elasticity, cost, and (optional) bounds.",
    )

    def predict(self, input_data: OptimalPricingIn) -> OptimalPricingOut:
        eps = input_data.elasticity_estimate
        p0 = input_data.current_price
        q0 = input_data.current_units_sold
        mc = input_data.unit_cost

        # Margin-maximising price by Lerner mark-up: p* = MC × ε / (ε + 1) for ε < -1
        if eps < -1.0 and mc > 0:
            optimal = mc * eps / (eps + 1.0)
            confidence = "high" if -3 < eps < -1.2 else "medium"
        elif eps >= -1.0:
            # Inelastic demand → push price up (cap at +25% absent ceiling)
            optimal = p0 * 1.25
            confidence = "low"
        else:  # mc == 0 → free goods, fall back to revenue-max heuristic
            optimal = p0
            confidence = "low"

        # Apply bounds
        if input_data.price_floor is not None:
            optimal = max(optimal, input_data.price_floor)
        if input_data.price_ceiling is not None:
            optimal = min(optimal, input_data.price_ceiling)

        # Demand at new price (constant-elasticity)
        units_new = q0 * (optimal / p0) ** eps
        rev_new = optimal * units_new
        margin_new = (optimal - mc) * units_new
        rev_old = p0 * q0
        margin_old = (p0 - mc) * q0

        rev_lift = (rev_new - rev_old) / rev_old * 100 if rev_old > 0 else 0.0
        margin_lift = (margin_new - margin_old) / margin_old * 100 if margin_old > 0 else 0.0

        return OptimalPricingOut(
            optimal_price=round(optimal, 2),
            expected_units=round(units_new, 2),
            expected_revenue=round(rev_new, 2),
            expected_margin=round(margin_new, 2),
            revenue_lift_pct=round(rev_lift, 2),
            margin_lift_pct=round(margin_lift, 2),
            confidence=confidence,
        )

    def explain(self, input_data: OptimalPricingIn) -> dict:
        return {
            "elasticity": 0.50,
            "unit_cost": 0.30,
            "current_price": 0.20,
        }
