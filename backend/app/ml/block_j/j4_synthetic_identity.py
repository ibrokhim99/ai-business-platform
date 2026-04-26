import numpy as np
from xgboost import XGBClassifier

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_j import SyntheticIdentityIn, SyntheticIdentityOut


def _build_xgb() -> XGBClassifier:
    rng = np.random.RandomState(44)
    n = 2000

    file_age = rng.exponential(scale=24, size=n)              # months
    inquiries = rng.poisson(lam=2.0, size=n).astype(float)
    address_changes = rng.poisson(lam=1.0, size=n).astype(float)
    ssn_age = rng.uniform(0.4, 1.0, n)
    phone_tenure = rng.exponential(scale=18, size=n)
    email_tenure = rng.exponential(scale=24, size=n)
    distinct_names = 1 + rng.poisson(0.5, n).astype(float)
    employer_verifiable = rng.binomial(1, 0.85, n).astype(float)

    X = np.column_stack([file_age, inquiries, address_changes, ssn_age,
                         phone_tenure, email_tenure, distinct_names,
                         employer_verifiable])

    p = (
        - np.clip(file_age / 60, 0, 0.40)
        + np.clip(inquiries / 8, 0, 0.20)
        + np.clip(address_changes / 5, 0, 0.15)
        - np.clip((1.0 - ssn_age) * 0.4, 0, 0.30) * (-1)   # younger SSN-vs-age = riskier
        - np.clip(phone_tenure / 36, 0, 0.15)
        - np.clip(email_tenure / 48, 0, 0.15)
        + np.clip((distinct_names - 1) / 4, 0, 0.20)
        - employer_verifiable * 0.20
        + 0.30
    )
    p = np.clip(p, 0.02, 0.98)
    y = (rng.uniform(size=n) < p).astype(int)

    clf = XGBClassifier(
        n_estimators=120, max_depth=4, learning_rate=0.05,
        random_state=44, eval_metric="logloss", verbosity=0,
    )
    clf.fit(X, y)
    return clf


_XGB = _build_xgb()


@register_model("M-J4")
class SyntheticIdentityModel(BaseMLModel[SyntheticIdentityIn, SyntheticIdentityOut]):
    metadata = ModelMetadata(
        model_id="M-J4", block="J",
        name="Synthetic Identity Detection",
        version="1.0.0",
        algorithm="XGBoost classifier on credit-thinness + identity-tenure features",
        is_stub=False,
        feature_names=["credit_file_age", "inquiries_6m", "address_changes_24m",
                       "ssn_age_norm", "phone_tenure", "email_tenure",
                       "distinct_names_at_address", "employer_verifiable"],
        supported_explainers=["rule_based"],
        description="Detects synthetic-identity fraud (fabricated SSN/credit profiles).",
    )

    def predict(self, input_data: SyntheticIdentityIn) -> SyntheticIdentityOut:
        X = np.array([[
            float(input_data.credit_file_age_months),
            float(input_data.credit_inquiries_last_6m),
            float(input_data.address_changes_last_24m),
            input_data.ssn_age_norm,
            float(input_data.phone_tenure_months),
            float(input_data.email_tenure_months),
            float(input_data.distinct_names_at_address),
            1.0 if input_data.employer_verifiable else 0.0,
        ]])

        prob = float(_XGB.predict_proba(X)[0, 1])
        prob = round(min(max(prob, 0.01), 0.99), 4)

        factors: list[str] = []
        if input_data.credit_file_age_months < 12:
            factors.append("Thin credit file (<12 months)")
        if input_data.credit_inquiries_last_6m >= 6:
            factors.append("High inquiry velocity (≥6 in 6 months)")
        if input_data.ssn_age_norm < 0.7:
            factors.append("Identity-document age inconsistent with applicant age")
        if input_data.phone_tenure_months < 6 and input_data.email_tenure_months < 6:
            factors.append("Both phone and email tenure under 6 months")
        if input_data.distinct_names_at_address >= 4:
            factors.append("≥4 distinct names registered at the same address")
        if not input_data.employer_verifiable:
            factors.append("Employer could not be independently verified")

        if prob < 0.30:
            band = "low"
            steps = ["Standard KYC sufficient"]
        elif prob < 0.60:
            band = "medium"
            steps = ["Manual document review", "Independent phone verification"]
        else:
            band = "high"
            steps = [
                "Block application pending investigation",
                "Bureau cross-check (eCBSV / Experian Synthetic ID)",
                "In-person identity verification",
                "Refer to fraud operations team",
            ]

        return SyntheticIdentityOut(
            synthetic_probability=prob,
            is_synthetic=prob >= 0.60,
            confidence_band=band,
            contributing_factors=factors,
            verification_steps=steps,
        )

    def explain(self, input_data: SyntheticIdentityIn) -> dict:
        importances = _XGB.feature_importances_
        names = self.metadata.feature_names
        total = float(sum(importances)) or 1.0
        return {n: round(float(v / total), 3) for n, v in zip(names, importances)}
