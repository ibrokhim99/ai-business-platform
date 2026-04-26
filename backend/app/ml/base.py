"""
BaseMLModel — the single abstract interface that all 35 models implement.

Every model:
  1. Declares a `metadata` class attribute of type ModelMetadata
  2. Implements `predict(input_data)` → output schema
  3. Implements `explain(input_data)` → dict of feature contributions
  4. Can override `load(version)` to pull a trained artifact from MLflow

Stubs:
  - is_stub=True  → deterministic math, no MLflow artifact needed
  - is_stub=False → real ML artifact loaded via MLflow
"""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

# ─── Type variables ────────────────────────────────────────────────────────────
InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


# ─── Metadata ─────────────────────────────────────────────────────────────────
class ModelMetadata(BaseModel):
    model_id: str
    """e.g. 'M-A1'"""
    block: str
    """Single letter: A–G"""
    name: str
    version: str
    """Semantic version. Stubs use '0.x.x-stub'."""
    algorithm: str
    """Human-readable algorithm description."""
    is_stub: bool
    """True until a real trained artifact is available."""
    mlflow_run_id: str | None = None
    feature_names: list[str] = []
    supported_explainers: list[str] = []
    """e.g. ['shap_tree', 'shap_linear', 'rule_based']"""
    description: str = ""
    input_schema: str = ""
    output_schema: str = ""


# ─── Prediction result ─────────────────────────────────────────────────────────
class PredictionResult(BaseModel):
    model_id: str
    version: str
    is_stub: bool
    prediction: Any
    explanation: dict | None = None
    latency_ms: int = 0
    request_id: str = ""
    metadata: dict = {}


# ─── Base model ABC ────────────────────────────────────────────────────────────
class BaseMLModel(ABC, Generic[InputT, OutputT]):
    """
    Abstract base for every model in the platform.

    Subclasses must:
      - Set `metadata` as a class-level ModelMetadata instance
      - Implement `predict(input_data: InputT) -> OutputT`
      - Implement `explain(input_data: InputT) -> dict`
    """

    metadata: ModelMetadata  # must be overridden by every subclass

    # ── Core interface ─────────────────────────────────────────────────────────

    @abstractmethod
    def predict(self, input_data: InputT) -> OutputT:
        """Run inference and return typed output."""
        ...

    @abstractmethod
    def explain(self, input_data: InputT) -> dict:
        """
        Return a feature contribution dict.
        Stubs return rule-based dicts; real models return SHAP values.
        """
        ...

    # ── Loading ────────────────────────────────────────────────────────────────

    @classmethod
    def load(cls, version: str = "latest") -> "BaseMLModel":
        """
        Load a model instance.
        Default: return the stub (cls()).
        Real models override this to pull from MLflow.
        """
        return cls()

    # ── Convenience ───────────────────────────────────────────────────────────

    def get_metadata(self) -> ModelMetadata:
        return self.metadata

    def input_hash(self, input_data: InputT) -> str:
        """SHA-256 of the serialised input — used as Redis cache key."""
        raw = json.dumps(input_data.model_dump(), sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def to_prediction_result(
        self,
        input_data: InputT,
        include_explanation: bool = False,
        request_id: str = "",
    ) -> PredictionResult:
        """Predict (+ optionally explain) and wrap into standard envelope."""
        t0 = time.monotonic()
        output = self.predict(input_data)
        explanation = self.explain(input_data) if include_explanation else None
        latency = int((time.monotonic() - t0) * 1000)

        return PredictionResult(
            model_id=self.metadata.model_id,
            version=self.metadata.version,
            is_stub=self.metadata.is_stub,
            prediction=output.model_dump() if hasattr(output, "model_dump") else output,
            explanation=explanation,
            latency_ms=latency,
            request_id=request_id,
        )
