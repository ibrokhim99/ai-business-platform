from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, func, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PredictionLog(Base):
    """Immutable audit record for every model prediction."""
    __tablename__ = "prediction_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_id: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    output_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_stub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
