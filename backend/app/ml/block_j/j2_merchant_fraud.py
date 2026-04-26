import numpy as np
import lightgbm as lgb

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_j import MerchantFraudIn, MerchantFraudOut

# MCC fraud-prior coefficients (higher = more historically fraud-prone)
_MCC_FRAUD_PRIOR = {
    "5967": 0.65,  # Direct marketing — inbound telemarketing
    "5816": 0.60,  # Digital goods
    "7995": 0.70,  # Gambling
    "5933": 0.55,  # Pawn shops
    "5912": 0.20,  # Pharmacies
    "5411": 0.15,  # Grocery
    "5812": 0.25,  # Restaurants
    "7011": 0.35,  # Lodging
}
_DEFAULT_MCC_FRAUD = 0.35


def _build_lgb() -> lgb.LGBMClassifier:
    rng = np.random.RandomState(43)
    n = 2000

    chargeback = rng.beta(1.2, 30, n)            # mostly low, some tail
    refund = rng.beta(1.5, 25, n)
    cnp_pct = rng.uniform(0, 1, n)
    foreign_pct = rng.uniform(0, 0.6, n)
    velocity = rng.gamma(2.0, 30.0, n) / 100     # txns/day normalized
    tenure_norm = rng.uniform(0, 1, n)
    avg_ticket_log = rng.normal(3.5, 0.7, n)
    complaints = rng.poisson(1.0, n).astype(float)
    mcc_prior = rng.uniform(0.1, 0.7, n)

    X = np.column_stack([chargeback, refund, cnp_pct, foreign_pct,
                         velocity, tenure_norm, avg_ticket_log,
                         complaints, mcc_prior])

    p = (
        chargeback * 1.5
        + refund * 0.7
        + cnp_pct * 0.30
        + foreign_pct * 0.25
        + velocity * 0.15
        - tenure_norm * 0.30
        + np.clip(complaints / 10, 0, 0.20)
        + mcc_prior * 0.40
    )
    p = np.clip(p, 0.02, 0.98)
    y = (rng.uniform(size=n) < p).astype(int)

    clf = lgb.LGBMClassifier(
        n_estimators=120, max_depth=5, learning_rate=0.05,
        random_state=43, verbose=-1,
    )
    clf.fit(X, y)
    return clf


_LGB = _build_lgb()


@register_model("M-J2")
class MerchantFraudModel(BaseMLModel[MerchantFraudIn, MerchantFraudOut]):
    metadata = ModelMetadata(
        model_id="M-J2", block="J",
        name="Merchant Fraud Score",
        version="1.0.0",
        algorithm="LightGBM classifier on chargeback/velocity/tenure features",
        is_stub=False,
        feature_names=["chargeback_rate", "refund_rate", "pct_cnp",
                       "pct_foreign", "velocity_norm", "tenure_norm",
                       "avg_ticket_log", "complaints", "mcc_fraud_prior"],
        supported_explainers=["rule_based"],
        description="Merchant-level fraud risk score with monitor/restrict/suspend decision.",
    )

    def predict(self, input_data: MerchantFraudIn) -> MerchantFraudOut:
        tenure_norm = min(input_data.months_active / 36, 1.0)
        velocity = min(input_data.txn_velocity_per_day / 100, 5.0)
        ticket_log = float(np.log10(max(input_data.avg_ticket_size, 1.0)))
        mcc_prior = _MCC_FRAUD_PRIOR.get(input_data.mcc_code, _DEFAULT_MCC_FRAUD)

        X = np.array([[
            input_data.chargeback_rate_30d,
            input_data.refund_rate_30d,
            input_data.pct_cnp_transactions,
            input_data.pct_foreign_cards,
            velocity,
            tenure_norm,
            ticket_log,
            float(input_data.prior_complaints_count),
            mcc_prior,
        ]])

        prob = float(_LGB.predict_proba(X)[0, 1])
        prob = round(min(max(prob, 0.01), 0.99), 4)
        score = round(1000 * prob)

        factors: list[str] = []
        if input_data.chargeback_rate_30d > 0.02:
            factors.append(f"Chargeback rate {input_data.chargeback_rate_30d:.1%} above 2% benchmark")
        if input_data.months_active < 6:
            factors.append("Newly onboarded merchant (<6 months)")
        if input_data.pct_cnp_transactions > 0.6 and input_data.pct_foreign_cards > 0.3:
            factors.append("High CNP × foreign-card mix")
        if input_data.prior_complaints_count >= 3:
            factors.append("Multiple prior consumer complaints")
        if mcc_prior >= 0.55:
            factors.append("High-risk merchant category")

        if prob < 0.25:
            band, decision = "low", "monitor"
        elif prob < 0.50:
            band, decision = "medium", "monitor"
        elif prob < 0.75:
            band, decision = "high", "restrict"
        else:
            band, decision = "severe", "suspend"

        return MerchantFraudOut(
            fraud_score=float(score),
            fraud_probability=prob,
            risk_band=band,
            decision=decision,
            risk_factors=factors,
        )

    def explain(self, input_data: MerchantFraudIn) -> dict:
        importances = _LGB.feature_importances_
        names = self.metadata.feature_names
        total = sum(importances) or 1.0
        return {n: round(float(v / total), 3) for n, v in zip(names, importances)}
