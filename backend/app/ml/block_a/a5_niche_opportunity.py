import numpy as np
from xgboost import XGBRegressor

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_a import NicheOpportunityIn, NicheOpportunityOut

# ---------------------------------------------------------------------------
# Build and fit an XGBoost model once at module load using synthetic training
# data with realistic distributions.
# ---------------------------------------------------------------------------

def _build_xgb_model() -> XGBRegressor:
    rng = np.random.default_rng(seed=42)
    n = 500

    # Synthetic features with realistic distributions for Central Asian markets
    population_norm = rng.beta(2, 3, n)          # skewed toward smaller populations
    income_norm = rng.beta(3, 5, n)              # skewed toward lower incomes
    competitor_density = rng.exponential(0.3, n).clip(0, 1)  # sparse competition
    growth_rate_norm = rng.beta(2, 2, n)         # centered around medium growth

    X = np.column_stack([population_norm, income_norm, competitor_density, growth_rate_norm])

    # Synthetic label: opportunity score 0-100
    # High income, high population, low competition, high growth → high score
    score_raw = (
        30 * income_norm
        + 25 * population_norm
        + 25 * (1 - competitor_density)
        + 20 * growth_rate_norm
        + rng.normal(0, 3, n)  # realistic noise
    )
    y = np.clip(score_raw, 0, 100)

    model = XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )
    model.fit(X, y)
    return model


_MODEL: XGBRegressor = _build_xgb_model()

# Normalization bounds for input features
_POP_MAX = 3_000_000.0
_INCOME_MAX = 5_000.0
_COMP_MAX = 50.0
_GROWTH_MAX = 30.0


@register_model("M-A5")
class NicheOpportunityModel(BaseMLModel[NicheOpportunityIn, NicheOpportunityOut]):
    metadata = ModelMetadata(
        model_id="M-A5",
        block="A",
        name="Niche Opportunity Score",
        version="1.0.0",
        algorithm="XGBoost regressor trained on synthetic market data",
        is_stub=False,
        feature_names=["population", "avg_income", "competitor_count", "growth_rate_pct"],
        supported_explainers=["shap_tree"],
        description="Scores a niche opportunity 0–100 using a trained XGBoost model.",
    )

    def _featurize(self, input_data: NicheOpportunityIn) -> np.ndarray:
        pop_norm = float(np.clip(input_data.population / _POP_MAX, 0, 1))
        income_norm = float(np.clip(input_data.avg_income / _INCOME_MAX, 0, 1))
        comp_density = float(np.clip(input_data.competitor_count / _COMP_MAX, 0, 1))
        growth_norm = float(np.clip(input_data.growth_rate_pct / _GROWTH_MAX, 0, 1))
        return np.array([[pop_norm, income_norm, comp_density, growth_norm]])

    def predict(self, input_data: NicheOpportunityIn) -> NicheOpportunityOut:
        X = self._featurize(input_data)
        raw_score = float(_MODEL.predict(X)[0])
        score = float(np.clip(raw_score, 0, 100))

        # Feature importances from the XGBoost model
        importances = _MODEL.feature_importances_  # gain-based

        if score >= 75:
            rank = "excellent"
        elif score >= 55:
            rank = "good"
        elif score >= 35:
            rank = "moderate"
        else:
            rank = "poor"

        top_factors = {
            "population_score": round(float(importances[0]) * score, 1),
            "income_score": round(float(importances[1]) * score, 1),
            "competition_score": round(float(importances[2]) * score, 1),
            "growth_score": round(float(importances[3]) * score, 1),
        }

        return NicheOpportunityOut(
            opportunity_score=round(score, 1),
            rank=rank,
            top_factors=top_factors,
        )

    def explain(self, input_data: NicheOpportunityIn) -> dict:
        importances = _MODEL.feature_importances_
        feature_names = self.metadata.feature_names
        return {
            "feature_importances": {
                name: round(float(imp), 4)
                for name, imp in zip(feature_names, importances)
            },
            "model_type": "xgboost",
            "explainer": "gain_importance",
        }
