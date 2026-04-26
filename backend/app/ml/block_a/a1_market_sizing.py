import numpy as np
from scipy import stats

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_a import MarketSizingIn, MarketSizingOut

# MCC-specific category penetration rates (share of income spent in this category)
_PENETRATION_RATES: dict[str, float] = {
    "5812": 0.15,  # Restaurants
    "5814": 0.12,  # Fast Food
    "5411": 0.12,  # Grocery Stores
    "5912": 0.08,  # Drug Stores / Pharmacies
    "5661": 0.06,  # Shoe Stores
    "5699": 0.07,  # Clothing / Apparel
    "7372": 0.04,  # Software / IT Services
    "5045": 0.05,  # Computers / Electronics
    "5940": 0.03,  # Sports Goods
    "5999": 0.09,  # Misc Retail
}
_DEFAULT_PENETRATION = 0.10

# SAM / TAM and SOM / SAM ratios by niche competition proxy
_SAM_RATIO = 0.40
_SOM_RATIO = 0.25


@register_model("M-A1")
class MarketSizingModel(BaseMLModel[MarketSizingIn, MarketSizingOut]):
    metadata = ModelMetadata(
        model_id="M-A1",
        block="A",
        name="Market Sizing (TAM/SAM/SOM)",
        version="1.0.0",
        algorithm="Bayesian bottom-up with MCC penetration rates",
        is_stub=False,
        feature_names=["region_id", "mcc_code", "population", "avg_income"],
        supported_explainers=["rule_based"],
        description="Estimates TAM/SAM/SOM for a niche and location using Bayesian bottom-up methodology.",
    )

    def predict(self, input_data: MarketSizingIn) -> MarketSizingOut:
        penetration = _PENETRATION_RATES.get(input_data.mcc_code, _DEFAULT_PENETRATION)

        # TAM: total annual category spend in the region (monthly)
        tam = input_data.population * input_data.avg_income * penetration
        sam = tam * _SAM_RATIO
        som = sam * _SOM_RATIO

        # Bayesian confidence interval using log-normal assumption on SOM
        # Standard deviation modelled as 20% of SOM (coefficient of variation = 0.20)
        cv = 0.20
        sigma_log = np.sqrt(np.log(1 + cv**2))
        mu_log = np.log(som) - sigma_log**2 / 2
        ci_low = float(np.exp(stats.norm.ppf(0.05, loc=mu_log, scale=sigma_log)))
        ci_high = float(np.exp(stats.norm.ppf(0.95, loc=mu_log, scale=sigma_log)))

        return MarketSizingOut(
            tam=round(tam, 2),
            sam=round(sam, 2),
            som=round(som, 2),
            confidence_interval=[round(ci_low, 2), round(ci_high, 2)],
            methodology="bayesian_bottom_up_mcc_penetration",
        )

    def explain(self, input_data: MarketSizingIn) -> dict:
        penetration = _PENETRATION_RATES.get(input_data.mcc_code, _DEFAULT_PENETRATION)
        tam = input_data.population * input_data.avg_income * penetration
        population_contribution = input_data.population * _DEFAULT_PENETRATION * input_data.avg_income / tam
        income_contribution = input_data.avg_income * input_data.population * _DEFAULT_PENETRATION / tam
        return {
            "population_weight": round(population_contribution * 0.5, 4),
            "income_weight": round(income_contribution * 0.3, 4),
            "penetration_rate": round(penetration, 4),
            "mcc_code": input_data.mcc_code,
            "sam_ratio": _SAM_RATIO,
            "som_ratio": _SOM_RATIO,
        }
