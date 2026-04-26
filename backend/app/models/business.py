from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Date, func, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class BusinessProfile(Base):
    """MSB (Micro/Small Business) profile — central entity for platform predictions."""
    __tablename__ = "business_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False,
                                              comment="Bank's external customer identifier")
    mcc_code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    niche_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    monthly_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active",
        comment="active | closed | suspended | prospect"
    )
    extra_features: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )


class CreditApplication(Base):
    """Loan/credit application tied to a business profile."""
    __tablename__ = "credit_applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    business_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_amount: Mapped[float] = mapped_column(Float, nullable=False)
    loan_term_months: Mapped[int] = mapped_column(Integer, nullable=False, default=36)
    purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credit_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_grade: Mapped[str | None] = mapped_column(String(10), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    officer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_outputs: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
