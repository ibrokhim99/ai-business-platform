"""Block I — Operations & Supply Chain schemas (M-I1 through M-I5)."""
from pydantic import BaseModel, Field


# ── M-I1: Inventory Optimizer ────────────────────────────────────────────────
class InventoryOptimizerIn(BaseModel):
    sku_id: str
    annual_demand: float = Field(..., gt=0, description="Units expected to sell in a year")
    unit_cost: float = Field(..., gt=0)
    ordering_cost: float = Field(default=50.0, gt=0,
                                 description="Fixed cost per purchase order")
    holding_cost_pct: float = Field(default=0.20, gt=0, le=1,
                                    description="Annual holding cost as % of unit cost")
    lead_time_days: float = Field(default=14, gt=0)
    demand_std_daily: float = Field(default=0.0, ge=0)
    service_level: float = Field(default=0.95, gt=0, lt=1)


class InventoryOptimizerOut(BaseModel):
    economic_order_quantity: float
    reorder_point: float
    safety_stock: float
    annual_orders: float
    total_annual_cost: float
    target_service_level: float


# ── M-I2: Stockout Risk ──────────────────────────────────────────────────────
class StockoutRiskIn(BaseModel):
    sku_id: str
    on_hand_units: float = Field(..., ge=0)
    on_order_units: float = Field(default=0, ge=0)
    daily_demand_mean: float = Field(..., gt=0)
    daily_demand_std: float = Field(..., ge=0)
    lead_time_days_mean: float = Field(..., gt=0)
    lead_time_days_std: float = Field(default=0.0, ge=0)
    horizon_days: int = Field(default=30, ge=1)


class StockoutRiskOut(BaseModel):
    stockout_probability: float = Field(..., ge=0, le=1)
    expected_stockout_days: float
    days_of_cover: float
    risk_level: str = Field(..., description="'low' | 'medium' | 'high' | 'critical'")
    recommended_action: str


# ── M-I3: Supplier Risk Score ────────────────────────────────────────────────
class SupplierRiskIn(BaseModel):
    supplier_id: str
    months_active: int = Field(..., ge=0)
    on_time_delivery_rate: float = Field(..., ge=0, le=1)
    quality_defect_rate: float = Field(default=0.01, ge=0, le=1)
    payment_terms_days: int = Field(default=30, ge=0)
    payment_delay_avg_days: float = Field(default=0.0, ge=0)
    revenue_concentration_pct: float = Field(default=0.10, ge=0, le=1,
                                             description="% of buyer revenue tied to this supplier")
    single_source_flag: bool = Field(default=False)
    geopolitical_risk: float = Field(default=0.30, ge=0, le=1)


class SupplierRiskOut(BaseModel):
    risk_score: float = Field(..., ge=0, le=1000)
    risk_band: str = Field(..., description="'low' | 'medium' | 'high' | 'severe'")
    primary_risk_factor: str
    contingency_actions: list[str]


# ── M-I4: Staffing Optimizer ─────────────────────────────────────────────────
class StaffingOptimizerIn(BaseModel):
    location_id: str
    hourly_demand: list[float] = Field(..., min_length=24, max_length=24,
                                       description="Forecast units of demand per hour (length 24)")
    units_per_staff_hour: float = Field(default=10.0, gt=0)
    min_staff_per_open_hour: int = Field(default=1, ge=0)
    max_staff: int = Field(default=20, ge=1)
    hourly_wage: float = Field(default=15.0, ge=0)
    open_hour: int = Field(default=8, ge=0, le=23)
    close_hour: int = Field(default=22, ge=0, le=23)


class StaffingOptimizerOut(BaseModel):
    hourly_staff: list[int] = Field(..., min_length=24, max_length=24)
    total_staff_hours: float
    estimated_labor_cost: float
    peak_hour: int
    peak_hour_staff: int


# ── M-I5: Delivery Routing ───────────────────────────────────────────────────
class RoutingStop(BaseModel):
    stop_id: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    demand: float = Field(default=1.0, ge=0)


class DeliveryRoutingIn(BaseModel):
    depot_lat: float = Field(..., ge=-90, le=90)
    depot_lon: float = Field(..., ge=-180, le=180)
    stops: list[RoutingStop] = Field(..., min_length=1)
    vehicle_capacity: float = Field(default=100.0, gt=0)
    n_vehicles: int = Field(default=4, ge=1, le=20)


class RouteOut(BaseModel):
    vehicle_id: int
    stop_sequence: list[str]
    distance_km: float
    load: float


class DeliveryRoutingOut(BaseModel):
    routes: list[RouteOut]
    total_distance_km: float
    n_vehicles_used: int
    unrouted_stops: list[str]
    method: str = "clarke_wright_savings"
