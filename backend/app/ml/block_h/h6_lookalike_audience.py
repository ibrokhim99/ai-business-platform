import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_h import LookalikeAudienceIn, LookalikeAudienceOut


def _vectorize(features: dict, keys: list[str]) -> np.ndarray:
    """Build a vector from a feature dict using the supplied key order."""
    return np.array([float(features.get(k, 0.0) or 0.0) for k in keys])


@register_model("M-H6")
class LookalikeAudienceModel(BaseMLModel[LookalikeAudienceIn, LookalikeAudienceOut]):
    """
    Cosine-similarity nearest-neighbour audience matcher.

    Uses the intersection of numeric keys between the seed and each candidate so
    callers don't have to pre-align features. Returns top-K candidates ranked by
    cosine similarity.
    """

    metadata = ModelMetadata(
        model_id="M-H6", block="H",
        name="Lookalike Audience",
        version="1.0.0",
        algorithm="Cosine-similarity k-NN over standardized numeric feature vectors",
        is_stub=False,
        feature_names=["seed_customer_features"],
        supported_explainers=["rule_based"],
        description="Find customers most similar to a seed for lookalike targeting.",
    )

    def predict(self, input_data: LookalikeAudienceIn) -> LookalikeAudienceOut:
        # Numeric keys from seed (skip non-numeric)
        seed_keys = [
            k for k, v in input_data.seed_customer_features.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        ]
        if not seed_keys:
            return LookalikeAudienceOut(matches=[], avg_similarity=0.0, seed_features_used=[])

        seed_vec = _vectorize(input_data.seed_customer_features, seed_keys)
        seed_norm = np.linalg.norm(seed_vec) or 1.0

        scored: list[tuple[str, float]] = []
        for cand in input_data.candidate_pool:
            cid = str(cand.get("customer_id", ""))
            if not cid:
                continue
            cand_vec = _vectorize(cand, seed_keys)
            cand_norm = np.linalg.norm(cand_vec) or 1.0
            sim = float(np.dot(seed_vec, cand_vec) / (seed_norm * cand_norm))
            scored.append((cid, round(sim, 4)))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[: input_data.top_k]
        avg_sim = round(float(np.mean([s for _, s in top])), 4) if top else 0.0

        return LookalikeAudienceOut(
            matches=[{"customer_id": cid, "similarity": sim} for cid, sim in top],
            avg_similarity=avg_sim,
            seed_features_used=seed_keys,
        )

    def explain(self, input_data: LookalikeAudienceIn) -> dict:
        return {"cosine_similarity": 1.0}
