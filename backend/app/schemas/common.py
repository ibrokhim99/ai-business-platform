"""Shared Pydantic schemas used across all blocks."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ExplainabilityOut(BaseModel):
    method: str
    is_stub: bool = False
    shap_values: dict[str, float] | None = None
    top_features: dict[str, float] | None = None
    factors: dict[str, Any] | None = None
    summary: str | None = None


class ModelPredictionResponse(BaseModel, Generic[DataT]):
    model_id: str
    version: str
    is_stub: bool
    latency_ms: int
    request_id: str = ""
    prediction: DataT
    explanation: ExplainabilityOut | None = None


class ModelMetadataOut(BaseModel):
    model_id: str
    block: str
    name: str
    version: str
    algorithm: str
    is_stub: bool
    feature_names: list[str]
    supported_explainers: list[str]
    description: str = ""
    mlflow_versions: list[dict[str, Any]] = Field(default_factory=list)


class ModelCatalogResponse(BaseModel):
    total: int
    models: list[ModelMetadataOut]


class TrainingJobOut(BaseModel):
    job_id: str
    model_id: str
    status: str
    enqueued_at: str


class ErrorResponse(BaseModel):
    detail: str
    code: str = "error"


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    services: dict[str, str] = Field(default_factory=dict)
