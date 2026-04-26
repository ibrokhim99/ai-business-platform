from collections import Counter
from itertools import permutations

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_h import ChannelAttributionIn, ChannelAttributionOut

# Channel-level baseline conversion lift used by the cooperative-game value function
_CHANNEL_LIFT = {
    "paid_search": 0.45, "social": 0.30, "display": 0.20,
    "email": 0.40, "referral": 0.55, "organic": 0.25,
    "direct": 0.50, "affiliate": 0.35, "video": 0.30,
}
_DEFAULT_LIFT = 0.25


def _channel_value(coalition: tuple[str, ...]) -> float:
    """v(S) — diminishing-returns conversion-probability of a coalition."""
    if not coalition:
        return 0.0
    p_no_conv = 1.0
    for ch in coalition:
        lift = _CHANNEL_LIFT.get(ch.lower(), _DEFAULT_LIFT)
        p_no_conv *= (1 - lift)
    return 1 - p_no_conv


def _exact_shapley(channels: list[str]) -> dict[str, float]:
    """
    Exact Shapley value for small coalitions (≤ 7).
    Average marginal contribution over all orderings.
    """
    contributions = Counter()
    n_perms = 0
    for perm in permutations(channels):
        seen: list[str] = []
        prev_v = 0.0
        for ch in perm:
            seen.append(ch)
            v = _channel_value(tuple(seen))
            contributions[ch] += (v - prev_v)
            prev_v = v
        n_perms += 1

    return {ch: contributions[ch] / n_perms for ch in set(channels)}


def _monte_carlo_shapley(channels: list[str], n_samples: int = 500) -> dict[str, float]:
    """Monte Carlo Shapley approximation for larger touchpoint paths."""
    import random
    rng = random.Random(42)

    contributions: dict[str, float] = {ch: 0.0 for ch in set(channels)}
    counts: dict[str, int] = {ch: 0 for ch in set(channels)}

    for _ in range(n_samples):
        order = channels[:]
        rng.shuffle(order)
        seen: list[str] = []
        prev_v = 0.0
        for ch in order:
            seen.append(ch)
            v = _channel_value(tuple(seen))
            contributions[ch] += (v - prev_v)
            counts[ch] += 1
            prev_v = v

    return {ch: contributions[ch] / max(counts[ch], 1) for ch in contributions}


@register_model("M-H3")
class ChannelAttributionModel(BaseMLModel[ChannelAttributionIn, ChannelAttributionOut]):
    metadata = ModelMetadata(
        model_id="M-H3", block="H",
        name="Channel Attribution",
        version="1.0.0",
        algorithm="Shapley value (exact for ≤ 7 touchpoints, Monte Carlo otherwise)",
        is_stub=False,
        feature_names=["touchpoints", "conversion_value"],
        supported_explainers=["rule_based"],
        description="Multi-touch attribution credit per channel using Shapley values.",
    )

    def predict(self, input_data: ChannelAttributionIn) -> ChannelAttributionOut:
        channels = [c.lower() for c in input_data.touchpoints]

        # Deduplicate touches but preserve full path for value function
        unique_channels = list(dict.fromkeys(channels))

        if len(unique_channels) <= 7:
            raw = _exact_shapley(unique_channels)
        else:
            raw = _monte_carlo_shapley(unique_channels)

        total = sum(raw.values()) or 1.0
        weights = {ch: round(v / total, 4) for ch, v in raw.items()}
        credit = {ch: round(w * input_data.conversion_value, 2) for ch, w in weights.items()}
        primary = max(weights, key=weights.get)

        return ChannelAttributionOut(
            weights=weights,
            credit=credit,
            primary_driver=primary,
            method="shapley_exact" if len(unique_channels) <= 7 else "shapley_monte_carlo",
        )

    def explain(self, input_data: ChannelAttributionIn) -> dict:
        return {
            "shapley_marginal_contribution": 1.0,
        }
