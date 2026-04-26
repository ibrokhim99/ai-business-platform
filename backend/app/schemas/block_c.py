"""Block C — Location Assessment & Traffic schemas (M-C1 through M-C6)."""
from pydantic import BaseModel, Field


# ── M-C1: Location Score ──────────────────────────────────────────────────────
class LocationScoreIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    mcc_code: str
    radius_m: int = Field(default=500, ge=100, le=2000)


class LocationScoreOut(BaseModel):
    score: float = Field(..., ge=0, le=100)
    grade: str = Field(..., description="'A' | 'B' | 'C' | 'D' | 'F'")
    sub_scores: dict[str, float] = Field(
        ...,
        description="traffic, competition, vitality, anchor, visibility, isochrone, demographic, income"
    )
    recommendation: str


# ── M-C2: Traffic Scoring ─────────────────────────────────────────────────────
class TrafficScoringIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_m: int = Field(default=200, ge=50, le=1000)


class TrafficScoringOut(BaseModel):
    daily_foot_traffic: int
    daily_auto_traffic: int
    peak_hours: list[int] = Field(..., description="Hours of day (0-23) with highest traffic")
    peak_days: list[str]
    hourly_profile: list[float] = Field(..., description="24 relative traffic multipliers")
    seasonal_factor: float


# ── M-C3: Isochrone Demand ────────────────────────────────────────────────────
class IsochroneDemandIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    walk_minutes: list[int] = Field(default=[5, 10])
    mcc_code: str


class IsochroneDemandOut(BaseModel):
    zones: list[dict] = Field(
        ...,
        description="{minutes, area_sqkm, population, consumer_potential_usd}"
    )
    total_addressable_population: int
    total_consumer_potential_usd: float


# ── M-C4: Street Vitality Index ───────────────────────────────────────────────
class StreetVitalityIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_m: int = Field(default=300, ge=50, le=1000)


class StreetVitalityOut(BaseModel):
    vitality_index: float = Field(..., ge=0, le=100)
    active_storefronts: int
    vacant_storefronts: int
    poi_count: int
    dominant_categories: list[str]


# ── M-C5: Anchor Effect Model ─────────────────────────────────────────────────
class AnchorEffectIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_m: int = Field(default=500, ge=100, le=2000)


class AnchorEffectOut(BaseModel):
    anchor_boost_pct: float = Field(..., description="% traffic lift from nearby anchors")
    anchors: list[dict] = Field(..., description="{name, type, distance_m, gravity_score}")
    dominant_anchor: str | None


# ── M-C6: Visibility Score ────────────────────────────────────────────────────
class VisibilityScoreIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    facade_direction_deg: float = Field(default=0, ge=0, le=360)


class VisibilityScoreOut(BaseModel):
    visibility_score: float = Field(..., ge=0, le=100)
    road_frontage_m: float
    sidewalk_width_m: float | None
    sight_lines: dict[str, float] = Field(..., description="Visibility distances by direction")
    obstructions: list[str]
