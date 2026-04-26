import numpy as np
from scipy.stats import expon
from xgboost import XGBClassifier

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_e import ChurnPredictionIn, ChurnPredictionOut

# MCC risk factors (higher = higher baseline churn risk)
_MCC_RISK = {
    "5812": 0.55, "5813": 0.60, "5411": 0.35,
    "5912": 0.30, "5651": 0.45, "7011": 0.50,
}
_DEFAULT_MCC_RISK = 0.45


def _mcc_risk(mcc_code: str) -> float:
    return _MCC_RISK.get(mcc_code, _DEFAULT_MCC_RISK)


def _build_model() -> XGBClassifier:
    rng = np.random.RandomState(42)
    n = 1000
    revenue_inv_ratio = rng.uniform(0.01, 2.0, n)
    owner_exp = rng.uniform(0, 20, n)
    location_score = rng.uniform(0, 100, n)
    competition_density = rng.uniform(0, 10, n)
    mcc_risk = rng.uniform(0.25, 0.65, n)

    X = np.column_stack([revenue_inv_ratio, owner_exp, location_score,
                         competition_density, mcc_risk])

    # Deterministic closure probability target
    p = (
        0.5
        - revenue_inv_ratio * 0.2
        - owner_exp * 0.01
        - location_score * 0.003
        + competition_density * 0.02
        + mcc_risk * 0.3
    )
    p = np.clip(p, 0.05, 0.95)
    y = (rng.uniform(size=n) < p).astype(int)

    clf = XGBClassifier(
        n_estimators=50,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
        eval_metric="logloss",
        verbosity=0,
        use_label_encoder=False,
    )
    clf.fit(X, y)
    return clf


_MODEL = _build_model()


@register_model("M-E2")
class ChurnPredictionModel(BaseMLModel[ChurnPredictionIn, ChurnPredictionOut]):
    metadata = ModelMetadata(
        model_id="M-E2", block="E",
        name="Churn Prediction",
        version="1.0.0",
        algorithm="XGBoost classifier (1000-sample synthetic training)",
        is_stub=False,
        feature_names=["revenue_to_investment_ratio", "owner_experience",
                       "location_score", "competition_density", "mcc_risk_factor"],
        supported_explainers=["rule_based"],
        description="Business closure probability in first 2 years.",
    )

    def predict(self, input_data: ChurnPredictionIn) -> ChurnPredictionOut:
        rev_inv = input_data.monthly_revenue / max(input_data.initial_investment, 1)
        mcc_r = _mcc_risk(input_data.mcc_code)
        X = np.array([[rev_inv, input_data.owner_experience_years,
                       input_data.location_score, input_data.competition_count, mcc_r]])
        prob = float(_MODEL.predict_proba(X)[0, 1])
        prob = round(min(max(prob, 0.05), 0.95), 3)

        risk_level = "low" if prob < 0.30 else "medium" if prob < 0.55 else "high"

        risks = []
        if input_data.owner_experience_years < 1:
            risks.append("Low owner experience")
        if input_data.location_score < 40:
            risks.append("Poor location score")
        if input_data.competition_count > 5:
            risks.append("High local competition")
        payback = input_data.initial_investment / max(input_data.monthly_revenue * 0.15, 1)
        if payback > 24:
            risks.append("Long investment payback period (>24 months)")
        if mcc_r >= 0.55:
            risks.append("High-risk business category")

        # Kaplan-Meier-like survival curve using exponential hazard
        lam = prob / 24  # monthly hazard rate calibrated to 2-year probability
        survival = []
        for m in range(1, 25):
            s_prob = round(float(expon.sf(m, scale=1 / lam)), 3) if lam > 0 else 1.0
            s_prob = max(min(s_prob, 1.0), 0.0)
            survival.append({"month": m, "survival_probability": s_prob})

        return ChurnPredictionOut(
            closure_probability_2y=prob,
            risk_level=risk_level,
            top_risk_factors=risks,
            survival_curve=survival,
        )

    def explain(self, input_data: ChurnPredictionIn) -> dict:
        importances = _MODEL.feature_importances_
        names = self.metadata.feature_names
        total = sum(importances) or 1.0
        return {n: round(float(v / total), 3) for n, v in zip(names, importances)}
