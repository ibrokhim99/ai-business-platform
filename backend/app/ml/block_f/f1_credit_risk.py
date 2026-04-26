import numpy as np
import lightgbm as lgb

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_f import CreditRiskIn, CreditRiskOut

# MCC risk coefficients (higher = riskier sector)
_MCC_RISK = {
    "5812": 0.55, "5813": 0.65, "5912": 0.30, "5047": 0.35,
    "5411": 0.40, "7011": 0.50, "5651": 0.45, "7372": 0.25,
}
_DEFAULT_MCC_RISK = 0.45

# Location risk proxy by region_id hash (0 = low, 1 = high risk)
_REGION_RISK = {
    "tashkent": 0.20, "samarkand": 0.35, "bukhara": 0.40,
    "namangan": 0.45, "fergana": 0.40, "andijan": 0.45,
}
_DEFAULT_REGION_RISK = 0.40

_GRADE_BANDS = [
    (800, "AAA", "approve",      0.02),
    (700, "AA",  "approve",      0.04),
    (600, "A",   "approve",      0.07),
    (500, "BBB", "conditional",  0.12),
    (400, "BB",  "conditional",  0.20),
    (300, "B",   "reject",       0.35),
    (0,   "CCC", "reject",       0.55),
]


def _build_lgb() -> lgb.LGBMClassifier:
    rng = np.random.RandomState(42)
    n = 2000

    cred_hist = rng.uniform(0, 1, n)
    rev_coverage = rng.uniform(0.01, 5.0, n)
    age_norm = rng.uniform(0, 1, n)
    collateral_ratio = rng.uniform(0, 3.0, n)
    loc_risk = rng.uniform(0.1, 0.9, n)
    mcc_risk = rng.uniform(0.2, 0.7, n)

    X = np.column_stack([cred_hist, rev_coverage, age_norm,
                         collateral_ratio, loc_risk, mcc_risk])

    # Deterministic default probability
    p = (
        0.5
        - cred_hist * 0.30
        - np.clip(rev_coverage / 5, 0, 0.20)
        - age_norm * 0.10
        - np.clip(collateral_ratio / 3, 0, 0.15)
        + loc_risk * 0.15
        + mcc_risk * 0.20
    )
    p = np.clip(p, 0.02, 0.98)
    y = (rng.uniform(size=n) < p).astype(int)

    clf = lgb.LGBMClassifier(
        n_estimators=80,
        max_depth=4,
        learning_rate=0.05,
        random_state=42,
        verbose=-1,
    )
    clf.fit(X, y)
    return clf


_LGB_MODEL = _build_lgb()


@register_model("M-F1")
class CreditRiskModel(BaseMLModel[CreditRiskIn, CreditRiskOut]):
    metadata = ModelMetadata(
        model_id="M-F1", block="F",
        name="Credit Risk Score",
        version="1.0.0",
        algorithm="LightGBM classifier (2000-sample synthetic training)",
        is_stub=False,
        feature_names=["normalized_credit_history", "revenue_coverage_ratio",
                       "business_age_norm", "collateral_ratio",
                       "location_risk", "mcc_risk"],
        supported_explainers=["rule_based"],
        description="Credit score 0–1000 with risk grade and loan decision.",
    )

    def predict(self, input_data: CreditRiskIn) -> CreditRiskOut:
        cred_hist_norm = (input_data.owner_credit_history_score - 300) / (850 - 300)
        rev_coverage = input_data.monthly_revenue_estimate / max(
            input_data.requested_loan_amount / 60, 1.0  # assume 60-month term
        )
        age_norm = min(input_data.business_age_months / 60, 1.0)
        collateral_ratio = input_data.collateral_value / max(input_data.requested_loan_amount, 1.0)
        loc_risk = _REGION_RISK.get(input_data.region_id.lower(), _DEFAULT_REGION_RISK)
        mcc_r = _MCC_RISK.get(input_data.mcc_code, _DEFAULT_MCC_RISK)

        X = np.array([[cred_hist_norm, rev_coverage, age_norm,
                       collateral_ratio, loc_risk, mcc_r]])

        default_prob = float(_LGB_MODEL.predict_proba(X)[0, 1])
        default_prob = round(min(max(default_prob, 0.01), 0.99), 4)

        # Map default probability to 0–1000 credit score (inverse relationship)
        credit_score = round(1000 * (1 - default_prob))
        credit_score = min(max(credit_score, 0), 1000)

        grade, decision, dp_override = "CCC", "reject", default_prob
        for threshold, g, d, dp in _GRADE_BANDS:
            if credit_score >= threshold:
                grade, decision, dp_override = g, d, dp
                break

        max_loan = round(input_data.monthly_revenue_estimate * 12 * 0.5, 2)
        conditions = []
        if decision == "conditional":
            if collateral_ratio < 0.5:
                conditions.append("Additional collateral required")
            conditions.append("Quarterly financial reporting required")
        elif decision == "reject" and credit_score >= 250:
            conditions.append("Reapply after 6 months with improved credit history")

        return CreditRiskOut(
            credit_score=float(credit_score),
            risk_grade=grade,
            default_probability=round(dp_override, 4),
            max_recommended_loan=max_loan,
            decision=decision,
            conditions=conditions,
        )

    def explain(self, input_data: CreditRiskIn) -> dict:
        importances = _LGB_MODEL.feature_importances_
        names = self.metadata.feature_names
        total = sum(importances) or 1.0
        return {n: round(float(v / total), 3) for n, v in zip(names, importances)}
