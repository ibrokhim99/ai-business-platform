import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_j import ApplicationFraudIn, ApplicationFraudOut


def _build_gbm() -> GradientBoostingClassifier:
    rng = np.random.RandomState(45)
    n = 2000

    apps_24h = rng.poisson(0.5, n).astype(float)
    apps_30d = rng.poisson(2.0, n).astype(float)
    device_share = rng.gamma(1.2, 1.0, n)
    ip_share = rng.gamma(1.2, 1.0, n)
    income_disc = rng.normal(0.0, 0.25, n)              # signed: pos = overstated
    doc_quality = rng.beta(8, 2, n)                     # most are high
    velocity = rng.beta(1.2, 6, n)
    geo_mismatch = rng.binomial(1, 0.12, n).astype(float)

    X = np.column_stack([apps_24h, apps_30d, device_share, ip_share,
                         np.abs(income_disc), doc_quality, velocity, geo_mismatch])

    p = (
        np.clip(apps_24h / 4, 0, 0.20)
        + np.clip(apps_30d / 12, 0, 0.20)
        + np.clip(device_share / 6, 0, 0.20)
        + np.clip(ip_share / 6, 0, 0.15)
        + np.clip(np.abs(income_disc), 0, 0.25)
        - doc_quality * 0.20
        + velocity * 0.20
        + geo_mismatch * 0.15
    )
    p = np.clip(p, 0.02, 0.98)
    y = (rng.uniform(size=n) < p).astype(int)

    clf = GradientBoostingClassifier(
        n_estimators=120, max_depth=3, learning_rate=0.05, random_state=45,
    )
    clf.fit(X, y)
    return clf


_GBM = _build_gbm()


@register_model("M-J5")
class ApplicationFraudModel(BaseMLModel[ApplicationFraudIn, ApplicationFraudOut]):
    metadata = ModelMetadata(
        model_id="M-J5", block="J",
        name="Application Fraud Detection",
        version="1.0.0",
        algorithm="GradientBoosting on application-velocity + identity-overlap features",
        is_stub=False,
        feature_names=["applications_24h", "applications_30d",
                       "device_seen_count", "ip_seen_count",
                       "income_discrepancy_abs", "document_quality",
                       "velocity_score", "geolocation_mismatch"],
        supported_explainers=["rule_based"],
        description="First-party fraud at loan/account origination — approve/review/deny.",
    )

    def predict(self, input_data: ApplicationFraudIn) -> ApplicationFraudOut:
        income_disc = (input_data.declared_income - input_data.bureau_income_estimate) / max(
            input_data.bureau_income_estimate, 1.0)
        income_disc_abs = abs(income_disc)

        X = np.array([[
            float(input_data.applications_last_24h),
            float(input_data.applications_last_30d),
            float(input_data.device_seen_count_30d),
            float(input_data.ip_seen_count_30d),
            income_disc_abs,
            input_data.document_quality_score,
            input_data.velocity_score,
            1.0 if input_data.geolocation_mismatch else 0.0,
        ]])

        prob = float(_GBM.predict_proba(X)[0, 1])
        prob = round(min(max(prob, 0.01), 0.99), 4)
        score = round(1000 * prob)

        indicators: list[str] = []
        if input_data.applications_last_24h >= 3:
            indicators.append("Multiple applications in 24h")
        if input_data.device_seen_count_30d >= 5:
            indicators.append("Device shared across many applicants in 30d")
        if input_data.ip_seen_count_30d >= 5:
            indicators.append("IP shared across many applicants in 30d")
        if income_disc_abs > 0.40:
            indicators.append(f"Declared income off bureau estimate by {income_disc_abs:.0%}")
        if input_data.document_quality_score < 0.5:
            indicators.append("Low document quality / signs of tampering")
        if input_data.geolocation_mismatch:
            indicators.append("Geolocation does not match declared address")
        if input_data.velocity_score > 0.7:
            indicators.append("High pre-computed velocity feature")

        if prob < 0.30:
            decision = "approve"
        elif prob < 0.65:
            decision = "review"
        else:
            decision = "deny"

        return ApplicationFraudOut(
            fraud_probability=prob,
            decision=decision,
            fraud_indicators=indicators,
            income_discrepancy_pct=round(income_disc * 100, 2),
            risk_score=float(score),
        )

    def explain(self, input_data: ApplicationFraudIn) -> dict:
        importances = _GBM.feature_importances_
        names = self.metadata.feature_names
        total = float(sum(importances)) or 1.0
        return {n: round(float(v / total), 3) for n, v in zip(names, importances)}
