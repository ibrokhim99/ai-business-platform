"""Block G — Social Profile & Target Audience schemas (M-G1 through M-G5)."""
from pydantic import BaseModel, Field


# ── M-G1: Customer Segment Profiler ──────────────────────────────────────────
class CustomerProfilerIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_m: int = Field(default=500, ge=100, le=2000)
    mcc_code: str


class CustomerProfilerOut(BaseModel):
    segments: list[dict] = Field(
        ...,
        description="{segment_id, label, share_pct, avg_age, avg_income, top_categories, visit_frequency}"
    )
    dominant_segment: str
    total_addressable_customers: int


# ── M-G2: Day Population Estimator ───────────────────────────────────────────
class DayPopulationIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_m: int = Field(default=500, ge=100, le=2000)
    hour_of_day: int = Field(default=12, ge=0, le=23)
    day_of_week: int = Field(default=1, ge=0, le=6, description="0=Mon, 6=Sun")


class DayPopulationOut(BaseModel):
    residents: int
    workers: int
    visitors: int
    transit_passers: int
    total_population: int
    hourly_profile: list[int] = Field(..., description="24 hourly population counts")


# ── M-G3: Consumer Behavior Classifier ───────────────────────────────────────
class BehaviorClassifierIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_m: int = Field(default=500, ge=100, le=2000)
    mcc_code: str


class BehaviorClassifierOut(BaseModel):
    consumer_types: list[dict] = Field(
        ...,
        description="{type, share_pct, peak_hours, avg_spend, description}"
    )
    dominant_type: str
    marketing_insight: str


# ── M-G4: Brand Affinity Model ────────────────────────────────────────────────
class BrandAffinityIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_m: int = Field(default=500, ge=100, le=2000)
    mcc_code: str


class BrandAffinityOut(BaseModel):
    chain_preference_pct: float = Field(..., ge=0, le=100)
    independent_preference_pct: float = Field(..., ge=0, le=100)
    top_chains: list[str]
    brand_loyalty_index: float = Field(..., ge=0, le=1)
    opportunity_type: str = Field(..., description="'chain' | 'independent' | 'mixed'")


# ── M-G5: Spending Power Index ────────────────────────────────────────────────
class SpendingPowerIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_m: int = Field(default=1000, ge=200, le=5000)


class SpendingPowerOut(BaseModel):
    spending_power_index: float = Field(..., ge=0, le=100)
    avg_monthly_spend_per_capita: float
    quartile: str = Field(..., description="'Q1' | 'Q2' | 'Q3' | 'Q4'")
    heatmap_cells: list[dict] = Field(
        ..., description="{lat, lon, index}"
    )
    category_breakdown: dict[str, float]
