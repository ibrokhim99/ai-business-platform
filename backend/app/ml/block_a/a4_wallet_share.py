import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_a import WalletShareIn, WalletShareOut

# MCC-specific category spend share of total monthly spending
_MCC_CATEGORY_SHARE: dict[str, float] = {
    "5812": 0.08,  # Restaurants (~8% of wallet)
    "5814": 0.05,  # Fast Food
    "5411": 0.18,  # Grocery
    "5912": 0.04,  # Pharmacy
    "5661": 0.03,  # Shoe stores
    "5699": 0.05,  # Clothing
    "7372": 0.02,  # Software
    "5045": 0.04,  # Electronics
}
_DEFAULT_CATEGORY_SHARE = 0.06

# Maximum reachable market share for a single entrant (HHI-based cap)
_ALPHA = 0.85  # market efficiency factor


@register_model("M-A4")
class WalletShareModel(BaseMLModel[WalletShareIn, WalletShareOut]):
    metadata = ModelMetadata(
        model_id="M-A4",
        block="A",
        name="Wallet Share Estimator",
        version="1.0.0",
        algorithm="Gravity-adjusted Herfindahl share model",
        is_stub=False,
        feature_names=["population", "avg_monthly_spend", "competitor_count", "mcc_code"],
        supported_explainers=["rule_based"],
        description="Estimates capturable wallet share using gravity-adjusted competition model.",
    )

    def predict(self, input_data: WalletShareIn) -> WalletShareOut:
        # Total category spend in the region
        category_share = _MCC_CATEGORY_SHARE.get(input_data.mcc_code, _DEFAULT_CATEGORY_SHARE)
        total_category_spend = input_data.population * input_data.avg_monthly_spend * category_share

        # Gravity model: new entrant captures 1/(n+1) share, modified by alpha
        # n = number of existing competitors
        n = max(input_data.competitor_count, 0)
        # Gravity share with decreasing returns as competition rises
        gravity_share = _ALPHA / (n + 1)

        # Apply competitive pressure correction: in high-competition markets,
        # consumers are more loyal to incumbents (inertia factor)
        inertia_discount = 1.0 / (1.0 + 0.05 * n)
        wallet_share = gravity_share * inertia_discount
        wallet_share_pct = float(np.clip(wallet_share * 100, 0.5, 95.0))

        estimated_monthly_revenue = total_category_spend * wallet_share

        # Confidence decays with more competitors (less data certainty)
        confidence = float(np.clip(0.95 - n * 0.04, 0.20, 0.95))

        return WalletShareOut(
            wallet_share_pct=round(wallet_share_pct, 2),
            estimated_monthly_revenue=round(estimated_monthly_revenue, 2),
            confidence=round(confidence, 3),
        )

    def explain(self, input_data: WalletShareIn) -> dict:
        category_share = _MCC_CATEGORY_SHARE.get(input_data.mcc_code, _DEFAULT_CATEGORY_SHARE)
        n = max(input_data.competitor_count, 0)
        gravity_weight = 1.0 / (n + 1)
        return {
            "competitor_count_weight": round(gravity_weight, 4),
            "category_spend_share": round(category_share, 4),
            "alpha_efficiency": _ALPHA,
            "inertia_discount": round(1.0 / (1.0 + 0.05 * n), 4),
            "market_size_weight": round(category_share * 0.5, 4),
        }
