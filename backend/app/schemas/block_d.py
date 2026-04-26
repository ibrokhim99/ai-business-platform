"""Block D — Financial Viability schemas (M-D1 through M-D6)."""
from pydantic import BaseModel, Field


# ── M-D1: Viability Check ─────────────────────────────────────────────────────
class ViabilityCheckIn(BaseModel):
    mcc_code: str
    region_id: str
    monthly_revenue_estimate: float = Field(..., gt=0)
    monthly_fixed_costs: float = Field(..., ge=0)
    initial_investment: float = Field(..., ge=0)
    monthly_rent: float = Field(..., ge=0)


class ViabilityCheckOut(BaseModel):
    survival_probability_2y: float = Field(..., ge=0, le=1)
    verdict: str = Field(..., description="'viable' | 'marginal' | 'high_risk'")
    key_risks: list[str]
    monthly_break_even: float
    months_to_break_even: float | None


# ── M-D2: Unit Economics ─────────────────────────────────────────────────────
class UnitEconomicsIn(BaseModel):
    mcc_code: str
    avg_transaction_value: float = Field(..., gt=0)
    monthly_transactions: int = Field(..., gt=0)
    customer_acquisition_cost: float = Field(..., ge=0)
    monthly_churn_rate_pct: float = Field(..., ge=0, le=100)
    gross_margin_pct: float = Field(..., ge=0, le=100)


class UnitEconomicsOut(BaseModel):
    ltv: float = Field(..., description="Lifetime Value (USD)")
    cac: float
    ltv_cac_ratio: float
    payback_months: float
    net_margin_pct: float
    unit_economics_grade: str


# ── M-D3: ROI Estimator ──────────────────────────────────────────────────────
class ROIEstimatorIn(BaseModel):
    initial_investment: float = Field(..., gt=0)
    monthly_net_cash_flow: float
    discount_rate_annual_pct: float = Field(default=12.0, ge=0, le=100)
    horizon_years: int = Field(default=3, ge=1, le=10)


class ROIEstimatorOut(BaseModel):
    npv: float
    irr_pct: float | None
    payback_months: float | None
    roi_pct: float
    verdict: str


# ── M-D4: Rental Burden Model ────────────────────────────────────────────────
class RentalBurdenIn(BaseModel):
    mcc_code: str
    monthly_revenue_estimate: float = Field(..., gt=0)
    monthly_rent: float = Field(..., gt=0)


class RentalBurdenOut(BaseModel):
    rent_to_revenue_pct: float
    safe_threshold_pct: float
    critical_threshold_pct: float
    status: str = Field(..., description="'safe' | 'warning' | 'critical'")
    max_affordable_rent: float


# ── M-D5: Cash Flow Simulator ────────────────────────────────────────────────
class CashFlowSimIn(BaseModel):
    mcc_code: str
    region_id: str
    initial_investment: float = Field(..., ge=0)
    monthly_revenue_base: float = Field(..., gt=0)
    monthly_fixed_costs: float = Field(..., ge=0)
    cogs_pct: float = Field(..., ge=0, le=100)
    growth_rate_monthly_pct: float = Field(default=0.0)
    horizon_months: int = Field(default=24, ge=6, le=36)


class CashFlowSimOut(BaseModel):
    monthly_cashflows: list[dict] = Field(
        ..., description="{month, revenue, costs, net_cashflow, cumulative}"
    )
    total_net: float
    cash_gap_months: list[int] = Field(..., description="Months with negative cumulative cash")
    break_even_month: int | None
    final_balance: float


# ── M-D6: COGS & Margin Estimator ────────────────────────────────────────────
class COGSMarginIn(BaseModel):
    mcc_code: str
    monthly_revenue: float = Field(..., gt=0)
    region_id: str = ""


class COGSMarginOut(BaseModel):
    cogs_pct: float
    gross_margin_pct: float
    operating_margin_pct: float
    net_margin_pct: float
    benchmark_source: str
    industry_comparison: str = Field(..., description="'above' | 'at' | 'below' benchmark")
