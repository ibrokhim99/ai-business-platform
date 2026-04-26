"""Block H — Marketing & Customer Acquisition schemas (M-H1 through M-H6)."""
from pydantic import BaseModel, Field


# ── M-H1: CAC Predictor ──────────────────────────────────────────────────────
class CACPredictorIn(BaseModel):
    channel: str = Field(..., description="'paid_search' | 'social' | 'referral' | 'display' | 'email' | 'organic'")
    region_id: str
    monthly_budget: float = Field(..., gt=0)
    industry_mcc: str
    target_segment: str = Field(default="smb", description="'smb' | 'consumer' | 'enterprise'")
    historical_cac: float = Field(default=0.0, ge=0,
                                  description="Prior-period CAC if known; 0 if cold start")
    competition_intensity: float = Field(default=0.5, ge=0, le=1)


class CACPredictorOut(BaseModel):
    predicted_cac: float = Field(..., gt=0)
    cac_range_low: float
    cac_range_high: float
    expected_acquisitions: float
    channel_efficiency: str = Field(..., description="'excellent' | 'good' | 'fair' | 'poor'")
    drivers: list[str]


# ── M-H2: LTV / CAC Ratio ────────────────────────────────────────────────────
class LTVCACRatioIn(BaseModel):
    arpu_monthly: float = Field(..., gt=0, description="Average revenue per user, monthly")
    gross_margin_pct: float = Field(..., ge=0, le=1)
    monthly_churn_rate: float = Field(..., gt=0, le=1)
    discount_rate_annual: float = Field(default=0.10, ge=0, le=1)
    cac: float = Field(..., gt=0)


class LTVCACRatioOut(BaseModel):
    ltv: float
    ltv_cac_ratio: float
    payback_months: float
    verdict: str = Field(..., description="'unsustainable' | 'marginal' | 'healthy' | 'excellent'")
    recommendations: list[str]


# ── M-H3: Channel Attribution ────────────────────────────────────────────────
class ChannelAttributionIn(BaseModel):
    journey_id: str
    touchpoints: list[str] = Field(..., min_length=1,
                                   description="Ordered list of channel touches before conversion")
    conversion_value: float = Field(..., gt=0)


class ChannelAttributionOut(BaseModel):
    weights: dict = Field(..., description="{channel: weight} summing to 1")
    credit: dict = Field(..., description="{channel: $ credit} summing to conversion_value")
    primary_driver: str
    method: str = "shapley_approximation"


# ── M-H4: Promo Uplift ───────────────────────────────────────────────────────
class PromoUpliftIn(BaseModel):
    customer_id: str
    promo_type: str = Field(..., description="'discount' | 'cashback' | 'free_trial' | 'bundle'")
    promo_value: float = Field(..., gt=0)
    customer_recency_days: int = Field(default=30, ge=0)
    customer_frequency_30d: int = Field(default=0, ge=0)
    customer_monetary_30d: float = Field(default=0.0, ge=0)
    historical_response_rate: float = Field(default=0.10, ge=0, le=1)


class PromoUpliftOut(BaseModel):
    uplift_probability: float = Field(..., description="P(buy | promo) - P(buy | no promo)")
    treated_response_prob: float = Field(..., ge=0, le=1)
    control_response_prob: float = Field(..., ge=0, le=1)
    expected_incremental_revenue: float
    target_decision: str = Field(..., description="'target' | 'skip' | 'do_not_disturb'")
    segment: str = Field(..., description="'persuadable' | 'sure_thing' | 'lost_cause' | 'sleeping_dog'")


# ── M-H5: Optimal Pricing ────────────────────────────────────────────────────
class OptimalPricingIn(BaseModel):
    product_id: str
    current_price: float = Field(..., gt=0)
    current_units_sold: float = Field(..., gt=0)
    unit_cost: float = Field(..., ge=0)
    elasticity_estimate: float = Field(default=-1.5, lt=0,
                                       description="Negative log-log price elasticity of demand")
    price_floor: float | None = None
    price_ceiling: float | None = None


class OptimalPricingOut(BaseModel):
    optimal_price: float
    expected_units: float
    expected_revenue: float
    expected_margin: float
    revenue_lift_pct: float
    margin_lift_pct: float
    confidence: str = Field(..., description="'low' | 'medium' | 'high'")


# ── M-H6: Lookalike Audience ─────────────────────────────────────────────────
class LookalikeAudienceIn(BaseModel):
    seed_customer_features: dict = Field(..., description="Numeric features describing the seed customer")
    candidate_pool: list[dict] = Field(..., min_length=1,
                                       description="List of candidate customer feature dicts (must include 'customer_id')")
    top_k: int = Field(default=10, ge=1, le=500)


class LookalikeAudienceOut(BaseModel):
    matches: list[dict] = Field(..., description="[{customer_id, similarity}], sorted by similarity desc")
    avg_similarity: float
    seed_features_used: list[str]
