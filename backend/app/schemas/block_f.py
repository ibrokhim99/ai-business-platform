"""Block F — Credit & Banking Products schemas (M-F1 through M-F5)."""
from pydantic import BaseModel, Field


# ── M-F1: Credit Risk Score ───────────────────────────────────────────────────
class CreditRiskIn(BaseModel):
    customer_id: str
    mcc_code: str
    region_id: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    monthly_revenue_estimate: float = Field(..., gt=0)
    requested_loan_amount: float = Field(..., gt=0)
    business_age_months: int = Field(default=0, ge=0)
    owner_credit_history_score: float = Field(default=500, ge=300, le=850)
    collateral_value: float = Field(default=0, ge=0)


class CreditRiskOut(BaseModel):
    credit_score: float = Field(..., ge=0, le=1000)
    risk_grade: str = Field(..., description="'AAA' | 'AA' | 'A' | 'BBB' | 'BB' | 'B' | 'CCC'")
    default_probability: float = Field(..., ge=0, le=1)
    max_recommended_loan: float
    decision: str = Field(..., description="'approve' | 'conditional' | 'reject'")
    conditions: list[str] = Field(default_factory=list)


# ── M-F2: Loan Sizing Recommender ─────────────────────────────────────────────
class LoanSizingIn(BaseModel):
    monthly_net_cashflow: float
    monthly_revenue: float = Field(..., gt=0)
    existing_debt_monthly: float = Field(default=0, ge=0)
    loan_term_months: int = Field(default=36, ge=6, le=120)
    interest_rate_annual_pct: float = Field(default=18.0, ge=0, le=100)


class LoanSizingOut(BaseModel):
    recommended_loan: float
    max_loan: float
    monthly_payment: float
    dti_ratio: float = Field(..., description="Debt-to-income ratio")
    affordability_verdict: str


# ── M-F3: DTI Predictor ───────────────────────────────────────────────────────
class DTIPredictorIn(BaseModel):
    mcc_code: str
    region_id: str
    initial_monthly_revenue: float = Field(..., gt=0)
    proposed_loan_amount: float = Field(..., gt=0)
    loan_term_months: int = Field(default=36, ge=6, le=120)
    interest_rate_annual_pct: float = Field(default=18.0)


class DTIPredictorOut(BaseModel):
    dti_at_6m: float
    dti_at_12m: float
    dti_at_24m: float
    safe_threshold: float = 0.43
    risk_periods: list[int] = Field(..., description="Months where DTI > safe_threshold")
    trajectory: str = Field(..., description="'improving' | 'stable' | 'deteriorating'")


# ── M-F4: NPL Early Warning ───────────────────────────────────────────────────
class NPLWarningIn(BaseModel):
    customer_id: str
    loan_id: str
    months_since_disbursement: int = Field(..., ge=0)
    payment_delays_count: int = Field(default=0, ge=0)
    revenue_trend_3m_pct: float = Field(default=0.0)
    current_dti: float = Field(..., ge=0)
    location_score: float = Field(default=50, ge=0, le=100)


class NPLWarningOut(BaseModel):
    npl_probability: float = Field(..., ge=0, le=1)
    alert_level: str = Field(..., description="'green' | 'yellow' | 'orange' | 'red'")
    days_to_potential_default: int | None
    recommended_actions: list[str]
    anomaly_flags: list[str]


# ── M-F5: Bank Product Recommender ────────────────────────────────────────────
class ProductRecommenderIn(BaseModel):
    customer_id: str
    mcc_code: str
    monthly_revenue: float = Field(..., gt=0)
    business_age_months: int = Field(default=0, ge=0)
    existing_products: list[str] = Field(default_factory=list)
    credit_score: float = Field(default=500, ge=300, le=1000)


class ProductRecommenderOut(BaseModel):
    recommendations: list[dict] = Field(
        ..., description="{product, type, score, rationale, amount_range}"
    )
    primary_recommendation: str
    cross_sell_opportunities: list[str]
