"""Block A — Market Analysis & Capacity schemas (M-A1 through M-A6)."""
from pydantic import BaseModel, Field


# ── M-A1: Market Sizing ───────────────────────────────────────────────────────
class MarketSizingIn(BaseModel):
    region_id: str = Field(..., description="Region identifier (e.g. 'tashkent-01')")
    mcc_code: str = Field(..., description="Merchant category code (e.g. '5812')")
    population: int = Field(..., gt=0)
    avg_income: float = Field(..., gt=0, description="Average monthly income (USD)")
    niche: str = Field(default="", description="Business niche label")


class MarketSizingOut(BaseModel):
    tam: float = Field(..., description="Total Addressable Market (USD/month)")
    sam: float = Field(..., description="Serviceable Addressable Market (USD/month)")
    som: float = Field(..., description="Serviceable Obtainable Market (USD/month)")
    confidence_interval: list[float] = Field(..., description="[low, high] 90% CI for SOM")
    methodology: str


# ── M-A2: GAP Analysis ────────────────────────────────────────────────────────
class GapAnalysisIn(BaseModel):
    region_id: str
    mcc_code: str
    normative_density: float = Field(..., description="Expected outlets per 10k population")
    actual_count: int = Field(..., ge=0)
    population: int = Field(..., gt=0)


class GapAnalysisOut(BaseModel):
    normative_count: float
    actual_count: int
    gap: float = Field(..., description="Positive = underserved, negative = oversaturated")
    gap_pct: float
    verdict: str = Field(..., description="'underserved' | 'balanced' | 'oversaturated'")


# ── M-A3: Saturation Index ────────────────────────────────────────────────────
class SaturationIndexIn(BaseModel):
    region_id: str
    mcc_code: str
    competitor_count: int = Field(..., ge=0)
    population: int = Field(..., gt=0)
    avg_revenue_per_outlet: float = Field(..., gt=0)


class SaturationIndexOut(BaseModel):
    saturation_index: float = Field(..., ge=0, le=100)
    level: str = Field(..., description="'low' | 'medium' | 'high' | 'critical'")
    components: dict[str, float]


# ── M-A4: Wallet Share Estimator ─────────────────────────────────────────────
class WalletShareIn(BaseModel):
    region_id: str
    mcc_code: str
    population: int = Field(..., gt=0)
    avg_monthly_spend: float = Field(..., gt=0)
    competitor_count: int = Field(..., ge=0)


class WalletShareOut(BaseModel):
    wallet_share_pct: float = Field(..., description="% of category spend capturable")
    estimated_monthly_revenue: float
    confidence: float = Field(..., ge=0, le=1)


# ── M-A5: Niche Opportunity Score ─────────────────────────────────────────────
class NicheOpportunityIn(BaseModel):
    region_id: str
    mcc_code: str
    population: int = Field(..., gt=0)
    avg_income: float = Field(..., gt=0)
    competitor_count: int = Field(..., ge=0)
    growth_rate_pct: float = Field(default=0.0)


class NicheOpportunityOut(BaseModel):
    opportunity_score: float = Field(..., ge=0, le=100)
    rank: str = Field(..., description="'excellent' | 'good' | 'moderate' | 'poor'")
    top_factors: dict[str, float]


# ── M-A6: Cross-Niche Cannibalization ─────────────────────────────────────────
class CrossNicheIn(BaseModel):
    new_mcc_code: str
    location_lat: float
    location_lon: float
    radius_m: int = Field(default=500, ge=100, le=2000)
    adjacent_mcc_codes: list[str] = Field(default_factory=list)


class CrossNicheOut(BaseModel):
    cannibalization_risk: float = Field(..., ge=0, le=1)
    affected_niches: list[dict]
    net_revenue_impact_pct: float
    recommendation: str
