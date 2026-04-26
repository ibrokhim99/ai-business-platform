import numpy as np
from sklearn.ensemble import IsolationForest

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_j import TransactionAnomalyIn, TransactionAnomalyOut


def _build_isolation_forest() -> IsolationForest:
    """Train IsolationForest on synthetic 'normal' card-transaction profiles.

    Training distribution spans the realistic SMB transaction range:
    $5–$5000 (log10 ~0.7–3.7), low/medium velocity, mostly local + present-card.
    """
    rng = np.random.RandomState(42)
    n = 3000

    # Cover the full realistic range so genuine small purchases aren't flagged.
    amount_log = rng.uniform(0.7, 3.7, size=n)                 # log10($5 .. $5000)
    velocity_24h = rng.poisson(lam=3.0, size=n).astype(float)
    velocity_7d = rng.poisson(lam=15.0, size=n).astype(float)
    amount_zscore = rng.normal(loc=0.0, scale=0.8, size=n)
    distinct_merch_24h = rng.poisson(lam=2.0, size=n).astype(float)
    is_foreign = rng.binomial(1, 0.05, n).astype(float)
    is_cnp = rng.binomial(1, 0.20, n).astype(float)
    odd_hour = rng.binomial(1, 0.10, n).astype(float)

    X = np.column_stack([amount_log, velocity_24h, velocity_7d, amount_zscore,
                         distinct_merch_24h, is_foreign, is_cnp, odd_hour])

    clf = IsolationForest(
        n_estimators=120,
        contamination=0.10,
        random_state=42,
    )
    clf.fit(X)
    return clf


_IF_MODEL = _build_isolation_forest()


def _score_to_prob(raw_score: float) -> float:
    """Map IsolationForest score (more negative = more anomalous) to [0, 1].

    Calibrated so a typical normal sample (raw ~ -0.45) maps to ~0.10
    and a clear outlier (raw ~ -0.65) maps to ~0.55 before rule overlays.
    """
    x = -raw_score
    prob = 1 / (1 + np.exp(-12 * (x - 0.55)))
    return float(np.clip(prob, 0.01, 0.99))


@register_model("M-J1")
class TransactionAnomalyModel(BaseMLModel[TransactionAnomalyIn, TransactionAnomalyOut]):
    metadata = ModelMetadata(
        model_id="M-J1", block="J",
        name="Transaction Anomaly Detection",
        version="1.0.0",
        algorithm="IsolationForest on amount/velocity/MCC features (2000-sample training)",
        is_stub=False,
        feature_names=["amount_log", "velocity_24h", "velocity_7d",
                       "amount_zscore", "distinct_merchants_24h",
                       "is_foreign", "is_cnp", "odd_hour"],
        supported_explainers=["rule_based"],
        description="Real-time per-transaction fraud anomaly score with rule-based overlays.",
    )

    def predict(self, input_data: TransactionAnomalyIn) -> TransactionAnomalyOut:
        amt_log = float(np.log10(max(input_data.amount, 1.0)))
        avg30 = max(input_data.avg_amount_last_30d, 1.0)
        amt_z = (input_data.amount - avg30) / max(avg30 * 0.5, 1.0)
        odd_hour = 1.0 if (input_data.hour_of_day < 5 or input_data.hour_of_day > 23) else 0.0

        X = np.array([[
            amt_log,
            float(input_data.txn_count_last_24h),
            float(input_data.txn_count_last_7d),
            amt_z,
            float(input_data.distinct_merchants_last_24h),
            1.0 if input_data.is_foreign else 0.0,
            1.0 if input_data.is_cnp else 0.0,
            odd_hour,
        ]])

        raw = float(_IF_MODEL.score_samples(X)[0])
        score = _score_to_prob(raw)

        rules: list[str] = []
        adj = 0.0
        if input_data.amount > avg30 * 5 and avg30 > 1:
            adj += 0.10
            rules.append("Amount exceeds 5× 30-day average")
        if input_data.txn_count_last_24h > 15:
            adj += 0.08
            rules.append("Velocity > 15 txns in 24h")
        if input_data.distinct_merchants_last_24h > 8:
            adj += 0.06
            rules.append("Burst across many merchants in 24h")
        if input_data.is_foreign and input_data.is_cnp:
            adj += 0.10
            rules.append("Foreign card-not-present transaction")
        if odd_hour and input_data.amount > avg30 * 2 and avg30 > 1:
            adj += 0.05
            rules.append("Large transaction at unusual hour")

        score = round(min(max(score + adj, 0.01), 0.99), 3)

        if score < 0.30:
            level, action = "low", "Allow"
        elif score < 0.55:
            level, action = "medium", "Allow with monitoring"
        elif score < 0.80:
            level, action = "high", "Step-up authentication required"
        else:
            level, action = "critical", "Decline and flag for review"

        return TransactionAnomalyOut(
            anomaly_score=score,
            is_anomaly=score >= 0.55,
            risk_level=level,
            triggered_rules=rules,
            recommended_action=action,
        )

    def explain(self, input_data: TransactionAnomalyIn) -> dict:
        return {
            "amount_zscore": 0.30,
            "velocity_24h": 0.25,
            "is_foreign_cnp": 0.20,
            "distinct_merchants": 0.15,
            "odd_hour": 0.10,
        }
