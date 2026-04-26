"""Block B — Forecasting & Demand schemas (M-B1 through M-B6)."""
from pydantic import BaseModel, Field


# ── M-B1: Demand Forecasting ──────────────────────────────────────────────────
class DemandForecastIn(BaseModel):
    region_id: str
    mcc_code: str
    horizon_months: int = Field(default=12, ge=1, le=36)
    base_monthly_revenue: float = Field(..., gt=0)


class DemandForecastOut(BaseModel):
    forecast: list[dict] = Field(..., description="List of {month, predicted, lower, upper}")
    trend: str = Field(..., description="'growing' | 'stable' | 'declining'")
    cagr_pct: float
    model_used: str


# ── M-B2: Seasonality Model ───────────────────────────────────────────────────
class SeasonalityIn(BaseModel):
    mcc_code: str
    region_id: str
    year: int = Field(..., ge=2020, le=2030)


class SeasonalityOut(BaseModel):
    monthly_indices: list[float] = Field(..., description="12 multipliers (1.0 = baseline)")
    peak_months: list[int]
    trough_months: list[int]
    events: list[dict] = Field(..., description="Named events with dates and impact")


# ── M-B3: Population Dynamics ─────────────────────────────────────────────────
class PopulationDynamicsIn(BaseModel):
    region_id: str
    horizon_years: int = Field(default=5, ge=1, le=20)


class PopulationDynamicsOut(BaseModel):
    projections: list[dict] = Field(..., description="List of {year, population, working_age_pct}")
    growth_rate_annual_pct: float
    demographic_shift: str


# ── M-B4: Income Trend Forecast ───────────────────────────────────────────────
class IncomeTrendIn(BaseModel):
    region_id: str
    horizon_months: int = Field(default=12, ge=3, le=36)
    current_avg_income: float = Field(..., gt=0)


class IncomeTrendOut(BaseModel):
    forecast: list[dict] = Field(..., description="{month, avg_income, lower, upper}")
    real_growth_rate_pct: float
    inflation_adjusted: bool = True


# ── M-B5: MCC Trend Detector ──────────────────────────────────────────────────
class MCCTrendIn(BaseModel):
    mcc_code: str
    region_id: str
    lookback_months: int = Field(default=24, ge=6, le=60)


class MCCTrendOut(BaseModel):
    trend_direction: str = Field(..., description="'growing' | 'declining' | 'stable' | 'volatile'")
    changepoints: list[dict] = Field(..., description="{date, type, magnitude}")
    momentum_score: float = Field(..., ge=-1, le=1)
    forecast_3m_pct: float


# ── M-B6: Business Registration Forecast ──────────────────────────────────────
class BusinessRegistrationIn(BaseModel):
    region_id: str
    mcc_code: str
    horizon_months: int = Field(default=12, ge=3, le=24)


class BusinessRegistrationOut(BaseModel):
    forecast: list[dict] = Field(..., description="{month, new_registrations, cumulative}")
    annual_growth_pct: float
    competition_intensity: str
