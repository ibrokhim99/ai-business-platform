from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ModelVersion(Base):
    """Tracks every trained model artifact, its MLflow run, and production status."""
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    artifact_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    is_stub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_production: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    trained_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dataset_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
