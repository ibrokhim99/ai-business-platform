import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_h import CACPredictorIn, CACPredictorOut

_CHANNEL_BASELINE = {
    "paid_search": 1.20, "social": 0.95, "display": 1.50,
    "email": 0.30, "referral": 0.40, "organic": 0.20,
}
_DEFAULT_CHANNEL = 1.00

_REGION_COST_MULT = {
    "tashkent": 1.20, "samarkand": 0.95, "bukhara": 0.90,
    "namangan": 0.85, "fergana": 0.85, "andijan": 0.85,
}
_DEFAULT_REGION_MULT = 1.00

_MCC_DIFFICULTY = {
    "5812": 1.00, "5814": 1.05, "5411": 0.85, "5912": 0.90,
    "7011": 1.20, "5651": 1.10, "7372": 1.30, "5816": 1.40,
}
_DEFAULT_MCC = 1.00


def _build_gbr() -> GradientBoostingRegressor:
    rng = np.random.RandomState(46)
    n = 2000

    channel_base = rng.uniform(0.2, 1.6, n)
    region_mult = rng.uniform(0.8, 1.3, n)
    mcc_diff = rng.uniform(0.8, 1.5, n)
    budget_log = rng.uniform(2, 5, n)        # log10($100 .. $100k)
    competition = rng.uniform(0, 1, n)
    has_history = rng.binomial(1, 0.6, n).astype(float)

    X = np.column_stack([channel_base, region_mult, mcc_diff,
                         budget_log, competition, has_history])

    # Synthetic CAC in dollars (log scale for stability)
    log_cac = (
        2.0
        + np.log(channel_base)
        + 0.30 * np.log(region_mult)
        + 0.45 * np.log(mcc_diff)
        - 0.10 * (budget_log - 3)         # mild scale economy
        + 0.40 * competition
        - 0.10 * has_history
    )
    y = np.exp(log_cac) * rng.uniform(0.85, 1.15, n)

    reg = GradientBoostingRegressor(n_estimators=120, max_depth=4,
                                    learning_rate=0.05, random_state=46)
    reg.fit(X, y)
    return reg


_GBR = _build_gbr()


@register_model("M-H1")
class CACPredictorModel(BaseMLModel[CACPredictorIn, CACPredictorOut]):
    metadata = ModelMetadata(
        model_id="M-H1", block="H",
        name="CAC Predictor",
        version="1.0.0",
        algorithm="GradientBoostingRegressor on channel × region × MCC × budget",
        is_stub=False,
        feature_names=["channel_baseline", "region_cost_mult", "mcc_difficulty",
                       "budget_log", "competition_intensity", "has_history"],
        supported_explainers=["rule_based"],
        description="Predicts customer acquisition cost per channel + budget plan.",
    )

    def predict(self, input_data: CACPredictorIn) -> CACPredictorOut:
        ch = _CHANNEL_BASELINE.get(input_data.channel.lower(), _DEFAULT_CHANNEL)
        rm = _REGION_COST_MULT.get(input_data.region_id.split("-")[0].lower(), _DEFAULT_REGION_MULT)
        mc = _MCC_DIFFICULTY.get(input_data.industry_mcc, _DEFAULT_MCC)
        budget_log = float(np.log10(max(input_data.monthly_budget, 1.0)))
        comp = input_data.competition_intensity
        has_hist = 1.0 if input_data.historical_cac > 0 else 0.0

        X = np.array([[ch, rm, mc, budget_log, comp, has_hist]])
        cac = float(_GBR.predict(X)[0])

        # Blend with historical CAC if provided (Bayesian-style shrinkage)
        if input_data.historical_cac > 0:
            cac = 0.7 * cac + 0.3 * input_data.historical_cac

        cac = max(round(cac, 2), 1.0)
        low = round(cac * 0.80, 2)
        high = round(cac * 1.25, 2)
        expected_acq = round(input_data.monthly_budget / cac, 1)

        if cac < 20:
            efficiency = "excellent"
        elif cac < 60:
            efficiency = "good"
        elif cac < 150:
            efficiency = "fair"
        else:
            efficiency = "poor"

        drivers: list[str] = []
        if ch >= 1.20:
            drivers.append(f"{input_data.channel} channel has structurally higher CAC")
        if rm >= 1.15:
            drivers.append("Region cost multiplier above baseline")
        if mc >= 1.20:
            drivers.append("Industry MCC is competitive (high CAC)")
        if comp >= 0.7:
            drivers.append("High competitive intensity inflating bid prices")
        if not drivers:
            drivers.append("Channel and market conditions are favorable")

        return CACPredictorOut(
            predicted_cac=cac,
            cac_range_low=low,
            cac_range_high=high,
            expected_acquisitions=expected_acq,
            channel_efficiency=efficiency,
            drivers=drivers,
        )

    def explain(self, input_data: CACPredictorIn) -> dict:
        importances = _GBR.feature_importances_
        names = self.metadata.feature_names
        total = float(sum(importances)) or 1.0
        return {n: round(float(v / total), 3) for n, v in zip(names, importances)}
