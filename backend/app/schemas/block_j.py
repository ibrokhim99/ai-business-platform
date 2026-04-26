"""Block J — Fraud, AML & Identity schemas (M-J1 through M-J5)."""
from pydantic import BaseModel, Field


# ── M-J1: Transaction Anomaly Detection ───────────────────────────────────────
class TransactionAnomalyIn(BaseModel):
    customer_id: str
    transaction_id: str
    amount: float = Field(..., gt=0, description="Transaction amount in local currency")
    mcc_code: str
    txn_count_last_24h: int = Field(default=0, ge=0)
    txn_count_last_7d: int = Field(default=0, ge=0)
    avg_amount_last_30d: float = Field(default=0.0, ge=0)
    distinct_merchants_last_24h: int = Field(default=0, ge=0)
    is_foreign: bool = Field(default=False)
    is_cnp: bool = Field(default=False, description="Card-not-present")
    hour_of_day: int = Field(default=12, ge=0, le=23)


class TransactionAnomalyOut(BaseModel):
    anomaly_score: float = Field(..., ge=0, le=1)
    is_anomaly: bool
    risk_level: str = Field(..., description="'low' | 'medium' | 'high' | 'critical'")
    triggered_rules: list[str]
    recommended_action: str


# ── M-J2: Merchant Fraud Score ────────────────────────────────────────────────
class MerchantFraudIn(BaseModel):
    merchant_id: str
    mcc_code: str
    months_active: int = Field(..., ge=0)
    chargeback_rate_30d: float = Field(default=0.0, ge=0, le=1)
    refund_rate_30d: float = Field(default=0.0, ge=0, le=1)
    avg_ticket_size: float = Field(..., gt=0)
    txn_velocity_per_day: float = Field(default=0.0, ge=0)
    pct_cnp_transactions: float = Field(default=0.0, ge=0, le=1)
    pct_foreign_cards: float = Field(default=0.0, ge=0, le=1)
    prior_complaints_count: int = Field(default=0, ge=0)


class MerchantFraudOut(BaseModel):
    fraud_score: float = Field(..., ge=0, le=1000)
    fraud_probability: float = Field(..., ge=0, le=1)
    risk_band: str = Field(..., description="'low' | 'medium' | 'high' | 'severe'")
    decision: str = Field(..., description="'monitor' | 'restrict' | 'suspend'")
    risk_factors: list[str]


# ── M-J3: AML Suspicious Pattern ──────────────────────────────────────────────
class AMLPatternIn(BaseModel):
    customer_id: str
    cash_deposits_last_7d: int = Field(default=0, ge=0)
    cash_amount_last_7d: float = Field(default=0.0, ge=0)
    structuring_threshold: float = Field(default=10000.0, gt=0,
                                         description="Reporting threshold (e.g. 10K)")
    near_threshold_deposits_30d: int = Field(default=0, ge=0,
                                             description="Deposits within 90% of threshold")
    rapid_in_out_count_30d: int = Field(default=0, ge=0,
                                        description="Funds in/out within 24h cycles")
    distinct_counterparties_30d: int = Field(default=0, ge=0)
    cross_border_count_30d: int = Field(default=0, ge=0)
    high_risk_jurisdiction_count: int = Field(default=0, ge=0)


class AMLPatternOut(BaseModel):
    suspicion_score: float = Field(..., ge=0, le=1)
    typology: str = Field(..., description="'structuring' | 'layering' | 'integration' | 'none'")
    sar_recommended: bool = Field(..., description="Suspicious Activity Report")
    triggered_typologies: list[str]
    confidence: float = Field(..., ge=0, le=1)


# ── M-J4: Synthetic Identity Detection ────────────────────────────────────────
class SyntheticIdentityIn(BaseModel):
    applicant_id: str
    credit_file_age_months: int = Field(default=0, ge=0)
    credit_inquiries_last_6m: int = Field(default=0, ge=0)
    address_changes_last_24m: int = Field(default=0, ge=0)
    ssn_age_norm: float = Field(default=1.0, ge=0, le=1,
                                description="Identity-document age relative to applicant age")
    phone_tenure_months: int = Field(default=0, ge=0)
    email_tenure_months: int = Field(default=0, ge=0)
    distinct_names_at_address: int = Field(default=1, ge=1)
    employer_verifiable: bool = Field(default=True)


class SyntheticIdentityOut(BaseModel):
    synthetic_probability: float = Field(..., ge=0, le=1)
    is_synthetic: bool
    confidence_band: str = Field(..., description="'low' | 'medium' | 'high'")
    contributing_factors: list[str]
    verification_steps: list[str]


# ── M-J5: Application Fraud Detection ─────────────────────────────────────────
class ApplicationFraudIn(BaseModel):
    application_id: str
    applications_last_24h: int = Field(default=0, ge=0)
    applications_last_30d: int = Field(default=0, ge=0)
    device_seen_count_30d: int = Field(default=1, ge=1,
                                       description="Distinct applicants on this device in 30d")
    ip_seen_count_30d: int = Field(default=1, ge=1)
    declared_income: float = Field(..., gt=0)
    bureau_income_estimate: float = Field(..., gt=0)
    document_quality_score: float = Field(default=1.0, ge=0, le=1)
    velocity_score: float = Field(default=0.0, ge=0, le=1,
                                  description="Pre-computed velocity feature")
    geolocation_mismatch: bool = Field(default=False)


class ApplicationFraudOut(BaseModel):
    fraud_probability: float = Field(..., ge=0, le=1)
    decision: str = Field(..., description="'approve' | 'review' | 'deny'")
    fraud_indicators: list[str]
    income_discrepancy_pct: float
    risk_score: float = Field(..., ge=0, le=1000)
