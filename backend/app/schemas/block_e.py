"""Block E — Competition & Risks schemas (M-E1 through M-E5)."""
from pydantic import BaseModel, Field


# ── M-E1: Competitor Intelligence ────────────────────────────────────────────
class CompetitorIntelIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    mcc_code: str
    radius_300m: bool = True
    radius_1km: bool = True


class CompetitorIntelOut(BaseModel):
    competitors_300m: list[dict]
    competitors_1km: list[dict]
    total_count: int
    avg_rating: float | None
    market_leader: str | None
    threat_level: str = Field(..., description="'low' | 'medium' | 'high' | 'critical'")


# ── M-E2: Churn Prediction ───────────────────────────────────────────────────
class ChurnPredictionIn(BaseModel):
    mcc_code: str
    region_id: str
    monthly_revenue: float = Field(..., gt=0)
    initial_investment: float = Field(..., gt=0)
    owner_experience_years: float = Field(default=0, ge=0)
    location_score: float = Field(default=50, ge=0, le=100)
    competition_count: int = Field(default=0, ge=0)


class ChurnPredictionOut(BaseModel):
    closure_probability_2y: float = Field(..., ge=0, le=1)
    risk_level: str = Field(..., description="'low' | 'medium' | 'high'")
    top_risk_factors: list[str]
    survival_curve: list[dict] = Field(..., description="{month, survival_probability}")


# ── M-E3: Regulatory Risk Score ──────────────────────────────────────────────
class RegulatoryRiskIn(BaseModel):
    mcc_code: str
    region_id: str
    business_age_months: int = Field(default=0, ge=0)


class RegulatoryRiskOut(BaseModel):
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: str = Field(..., description="'low' | 'medium' | 'high'")
    applicable_regulations: list[str]
    inspection_frequency: str
    common_violations: list[str]


# ── M-E4: Market Entry Barrier Index ─────────────────────────────────────────
class EntryBarrierIn(BaseModel):
    mcc_code: str
    region_id: str
    initial_investment: float = Field(..., gt=0)


class EntryBarrierOut(BaseModel):
    barrier_index: float = Field(..., ge=0, le=100)
    barrier_level: str = Field(..., description="'low' | 'medium' | 'high' | 'very_high'")
    components: dict[str, float] = Field(
        ..., description="capital, regulatory, brand_loyalty, economies_of_scale, switching_costs"
    )
    recommendation: str


# ── M-E5: Price Pressure Model ───────────────────────────────────────────────
class PricePressureIn(BaseModel):
    mcc_code: str
    region_id: str
    target_price: float = Field(..., gt=0)
    competitor_avg_price: float = Field(..., gt=0)


class PricePressureOut(BaseModel):
    price_pressure_score: float = Field(..., ge=0, le=1, description="1 = max pressure")
    optimal_price_range: list[float] = Field(..., description="[min, max]")
    price_elasticity: float
    recommended_price: float
    margin_at_recommended: float | None
