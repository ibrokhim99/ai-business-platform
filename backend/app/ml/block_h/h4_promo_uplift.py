import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_h import PromoUpliftIn, PromoUpliftOut


def _build_two_models() -> tuple[GradientBoostingClassifier, GradientBoostingClassifier]:
    """Two-model uplift: separate buy-prob estimators for treated and control groups."""
    rng = np.random.RandomState(47)
    n = 2000

    recency = rng.uniform(0, 365, n)
    frequency = rng.poisson(2, n).astype(float)
    monetary = rng.gamma(2.0, 100, n)
    promo_value = rng.uniform(5, 200, n)
    response_rate = rng.uniform(0.02, 0.40, n)
    promo_type = rng.choice([0, 1, 2, 3], n).astype(float)   # cat-coded

    X = np.column_stack([recency, frequency, monetary, promo_value,
                         response_rate, promo_type])

    # Treated: promo helps high-recency, low-frequency users a lot
    p_treated = (
        0.10
        + 0.30 * np.exp(-recency / 60)
        - 0.05 * np.clip(frequency / 5, 0, 1)
        + 0.20 * np.clip(monetary / 1000, 0, 1)
        + 0.25 * np.clip(promo_value / 100, 0, 1)
        + 0.40 * response_rate
    )
    p_treated = np.clip(p_treated, 0.02, 0.95)
    y_treated = (rng.uniform(size=n) < p_treated).astype(int)

    # Control: same RFM matters but no promo lift
    p_control = (
        0.05
        + 0.10 * np.exp(-recency / 60)
        + 0.10 * np.clip(monetary / 1000, 0, 1)
        + 0.30 * response_rate
    )
    p_control = np.clip(p_control, 0.01, 0.90)
    y_control = (rng.uniform(size=n) < p_control).astype(int)

    treated = GradientBoostingClassifier(n_estimators=100, max_depth=3,
                                          learning_rate=0.05, random_state=47)
    control = GradientBoostingClassifier(n_estimators=100, max_depth=3,
                                          learning_rate=0.05, random_state=48)
    treated.fit(X, y_treated)
    control.fit(X, y_control)
    return treated, control


_TREATED, _CONTROL = _build_two_models()

_PROMO_CODE = {"discount": 0, "cashback": 1, "free_trial": 2, "bundle": 3}


def _segment(treated_p: float, control_p: float) -> str:
    """Standard four-quadrant uplift segment labels."""
    if treated_p >= 0.50 and control_p >= 0.50:
        return "sure_thing"     # buys regardless — wasted promo
    if treated_p < 0.30 and control_p < 0.30:
        return "lost_cause"
    if treated_p > control_p + 0.05:
        return "persuadable"
    if treated_p < control_p - 0.05:
        return "sleeping_dog"   # promo causes them to NOT buy (negative uplift)
    return "lost_cause"


@register_model("M-H4")
class PromoUpliftModel(BaseMLModel[PromoUpliftIn, PromoUpliftOut]):
    metadata = ModelMetadata(
        model_id="M-H4", block="H",
        name="Promo Uplift Modeling",
        version="1.0.0",
        algorithm="Two-model uplift (treated vs control GBM, CATE estimate)",
        is_stub=False,
        feature_names=["recency", "frequency", "monetary",
                       "promo_value", "historical_response_rate", "promo_type"],
        supported_explainers=["rule_based"],
        description="Causal uplift segmentation: persuadable / sure_thing / lost_cause / sleeping_dog.",
    )

    def predict(self, input_data: PromoUpliftIn) -> PromoUpliftOut:
        promo_type = float(_PROMO_CODE.get(input_data.promo_type.lower(), 0))
        X = np.array([[
            float(input_data.customer_recency_days),
            float(input_data.customer_frequency_30d),
            float(input_data.customer_monetary_30d),
            input_data.promo_value,
            input_data.historical_response_rate,
            promo_type,
        ]])

        p_t = float(_TREATED.predict_proba(X)[0, 1])
        p_c = float(_CONTROL.predict_proba(X)[0, 1])
        uplift = p_t - p_c
        seg = _segment(p_t, p_c)

        # Expected incremental revenue = uplift × monetary baseline
        baseline_value = max(input_data.customer_monetary_30d, input_data.promo_value)
        incremental = uplift * baseline_value - (max(uplift, 0) * input_data.promo_value * 0.5)

        if seg == "persuadable":
            decision = "target"
        elif seg == "sleeping_dog":
            decision = "do_not_disturb"
        else:
            decision = "skip"

        return PromoUpliftOut(
            uplift_probability=round(uplift, 4),
            treated_response_prob=round(p_t, 4),
            control_response_prob=round(p_c, 4),
            expected_incremental_revenue=round(incremental, 2),
            target_decision=decision,
            segment=seg,
        )

    def explain(self, input_data: PromoUpliftIn) -> dict:
        importances = (_TREATED.feature_importances_ + _CONTROL.feature_importances_) / 2
        names = self.metadata.feature_names
        total = float(sum(importances)) or 1.0
        return {n: round(float(v / total), 3) for n, v in zip(names, importances)}
