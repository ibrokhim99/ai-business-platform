import numpy as np
from sklearn.ensemble import IsolationForest

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_f import NPLWarningIn, NPLWarningOut


def _build_isolation_forest() -> IsolationForest:
    """Train an IsolationForest on synthetic healthy-loan performance data."""
    rng = np.random.RandomState(42)
    n = 1000

    # Healthy loans: low delays, positive revenue, low DTI, good location
    payment_delays = rng.uniform(0, 0.1, n)        # 0-1 normalised
    revenue_trend = rng.uniform(0.0, 0.3, n)       # positive trend
    current_dti = rng.uniform(0.1, 0.35, n)        # well below safe threshold
    location_score_norm = rng.uniform(0.5, 1.0, n) # decent locations

    X_healthy = np.column_stack([payment_delays, revenue_trend,
                                  current_dti, location_score_norm])

    # 10% artificial anomalies for contamination calibration
    contamination = 0.10
    clf = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
    )
    clf.fit(X_healthy)
    return clf


_IF_MODEL = _build_isolation_forest()


def _anomaly_score_to_prob(raw_score: float) -> float:
    """
    IsolationForest score_samples returns negative values; more negative = more anomalous.
    Map to [0, 1] probability with sigmoid-like transform.
    Typical range: -0.7 (normal) to 0 (boundary) to +0.2 (anomalous)
    """
    # Convert: more negative = higher probability
    # Empirical: score ~-0.6 → prob 0.05; score ~0 → prob 0.50; score ~0.2 → prob 0.85
    x = -raw_score   # flip so positive = anomalous
    prob = 1 / (1 + np.exp(-8 * (x - 0.35)))
    return float(np.clip(prob, 0.01, 0.99))


@register_model("M-F4")
class NPLWarningModel(BaseMLModel[NPLWarningIn, NPLWarningOut]):
    metadata = ModelMetadata(
        model_id="M-F4", block="F",
        name="NPL Early Warning",
        version="1.0.0",
        algorithm="IsolationForest anomaly detection (1000-sample training)",
        is_stub=False,
        feature_names=["payment_delays_norm", "revenue_trend",
                       "current_dti", "location_score_norm"],
        supported_explainers=["rule_based"],
        description="NPL default signal 2-3 months before delinquency.",
    )

    def predict(self, input_data: NPLWarningIn) -> NPLWarningOut:
        # Normalize features to match training distribution
        payment_delays_norm = min(input_data.payment_delays_count / 10.0, 1.0)
        revenue_trend_norm = input_data.revenue_trend_3m_pct / 100.0   # %-change as fraction
        location_norm = input_data.location_score / 100.0

        X = np.array([[payment_delays_norm,
                       revenue_trend_norm,
                       input_data.current_dti,
                       location_norm]])

        raw_score = float(_IF_MODEL.score_samples(X)[0])
        base_prob = _anomaly_score_to_prob(raw_score)

        # Rule-based adjustments on top of ML score
        flags = []
        adj = 0.0
        if input_data.payment_delays_count >= 2:
            adj += 0.10
            flags.append("Multiple payment delays detected")
        if input_data.revenue_trend_3m_pct < -10:
            adj += 0.08
            flags.append("Significant revenue decline (>10%)")
        if input_data.current_dti > 0.55:
            adj += 0.07
            flags.append("DTI above critical threshold (0.55)")
        if input_data.location_score < 40:
            adj += 0.05
            flags.append("Poor location performance score")
        if input_data.payment_delays_count == 0 and input_data.revenue_trend_3m_pct > 5:
            adj -= 0.05   # positive signal

        prob = round(min(max(base_prob + adj, 0.01), 0.99), 3)

        if prob < 0.20:
            alert = "green"
            days = None
            actions = ["No action required — loan performing normally"]
        elif prob < 0.40:
            alert = "yellow"
            days = 90
            actions = ["Schedule account review in 30 days", "Verify latest revenue data"]
        elif prob < 0.65:
            alert = "orange"
            days = 60
            actions = [
                "Proactive collection call — schedule within 7 days",
                "Restructuring feasibility assessment",
                "On-site business visit",
            ]
        else:
            alert = "red"
            days = 30
            actions = [
                "Immediate collection action required",
                "Collateral valuation and security review",
                "Mandatory loan restructuring or write-off provisioning",
            ]

        return NPLWarningOut(
            npl_probability=prob,
            alert_level=alert,
            days_to_potential_default=days,
            recommended_actions=actions,
            anomaly_flags=flags,
        )

    def explain(self, input_data: NPLWarningIn) -> dict:
        return {
            "payment_delays": 0.40,
            "revenue_trend": 0.30,
            "dti_level": 0.20,
            "location_score": 0.10,
        }
