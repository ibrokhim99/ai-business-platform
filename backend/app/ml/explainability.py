"""
Explainability service — wraps SHAP and rule-based explanations.

Stubs return rule-based dicts (no SHAP import needed).
Real models return SHAP values via the appropriate explainer.
"""

from __future__ import annotations

from typing import Any

from app.ml.base import BaseMLModel


class ExplainabilityService:
    """
    Selects the right SHAP explainer based on model.metadata.supported_explainers
    and returns a unified explanation dict.
    """

    def explain(self, model: BaseMLModel, input_data: Any) -> dict:
        explainers = model.metadata.supported_explainers

        # Stubs — rule-based
        if model.metadata.is_stub or "rule_based" in explainers:
            raw = model.explain(input_data)
            return {
                "method": "rule_based",
                "is_stub": True,
                "factors": raw,
                "summary": "Stub explanation — replace with SHAP after model training.",
            }

        # Tree-based (XGBoost, LightGBM, RandomForest)
        if "shap_tree" in explainers:
            return self._shap_tree(model, input_data)

        # Linear models
        if "shap_linear" in explainers:
            return self._shap_linear(model, input_data)

        # Deep learning (LSTM, MLP)
        if "shap_gradient" in explainers:
            return self._shap_gradient(model, input_data)

        # Fallback to model's own explain()
        raw = model.explain(input_data)
        return {"method": "custom", "factors": raw}

    # ── SHAP helpers (only imported when needed) ────────────────────────────

    def _shap_tree(self, model: BaseMLModel, input_data: Any) -> dict:
        import shap
        import pandas as pd

        estimator = getattr(model, "_estimator", None)
        if estimator is None:
            return {"method": "shap_tree", "error": "No _estimator attribute on model."}

        features = model.metadata.feature_names
        X = pd.DataFrame([input_data.model_dump()])[features]
        explainer = shap.TreeExplainer(estimator)
        shap_values = explainer.shap_values(X)

        if hasattr(shap_values, "tolist"):
            values = shap_values[0].tolist()
        else:
            values = list(shap_values[0])

        shap_dict = dict(zip(features, values))
        top = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        summary = "; ".join(f"{k}: {v:+.3f}" for k, v in top)

        return {
            "method": "shap_tree",
            "shap_values": shap_dict,
            "top_features": dict(top),
            "summary": summary,
        }

    def _shap_linear(self, model: BaseMLModel, input_data: Any) -> dict:
        import shap
        import pandas as pd
        import numpy as np

        estimator = getattr(model, "_estimator", None)
        background = getattr(model, "_background_data", np.zeros((1, len(model.metadata.feature_names))))

        features = model.metadata.feature_names
        X = pd.DataFrame([input_data.model_dump()])[features]
        explainer = shap.LinearExplainer(estimator, background)
        shap_values = explainer.shap_values(X)
        shap_dict = dict(zip(features, shap_values[0].tolist()))

        return {"method": "shap_linear", "shap_values": shap_dict}

    def _shap_gradient(self, model: BaseMLModel, input_data: Any) -> dict:
        # Placeholder — real implementation requires torch tensor handling
        raw = model.explain(input_data)
        return {"method": "shap_gradient", "factors": raw}


# Module-level singleton
_explainability_service: ExplainabilityService | None = None


def get_explainability_service() -> ExplainabilityService:
    global _explainability_service
    if _explainability_service is None:
        _explainability_service = ExplainabilityService()
    return _explainability_service
