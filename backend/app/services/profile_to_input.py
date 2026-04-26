"""
Server-side port of frontend `buildInput` arrow functions from
`frontend/src/lib/chat/models.ts`.

Given a `ChatProfile` (loose, partial business profile maintained by the LLM
chat), `build(model_id, profile)` returns the right Pydantic input class for
that model, ready to feed to `PredictionService.predict`.

Keep this module the *only* place that knows how to map profile fields onto
each model's input schema.
"""
from __future__ import annotations

import uuid
from typing import Callable

from pydantic import BaseModel, Field

from app.schemas.block_a import (
    MarketSizingIn, GapAnalysisIn, SaturationIndexIn,
    WalletShareIn, NicheOpportunityIn, CrossNicheIn,
)
from app.schemas.block_b import (
    DemandForecastIn, SeasonalityIn, PopulationDynamicsIn,
    IncomeTrendIn, MCCTrendIn, BusinessRegistrationIn,
)
from app.schemas.block_c import (
    LocationScoreIn, TrafficScoringIn, IsochroneDemandIn,
    StreetVitalityIn, AnchorEffectIn, VisibilityScoreIn,
)
from app.schemas.block_d import (
    ViabilityCheckIn, UnitEconomicsIn, ROIEstimatorIn,
    RentalBurdenIn, CashFlowSimIn, COGSMarginIn,
)
from app.schemas.block_e import (
    CompetitorIntelIn, ChurnPredictionIn, RegulatoryRiskIn,
    EntryBarrierIn, PricePressureIn,
)
from app.schemas.block_f import (
    CreditRiskIn, LoanSizingIn, DTIPredictorIn,
    NPLWarningIn, ProductRecommenderIn,
)
from app.schemas.block_g import (
    CustomerProfilerIn, DayPopulationIn, BehaviorClassifierIn,
    BrandAffinityIn, SpendingPowerIn,
)
from app.schemas.block_h import (
    CACPredictorIn, LTVCACRatioIn, ChannelAttributionIn,
    PromoUpliftIn, OptimalPricingIn, LookalikeAudienceIn,
)
from app.schemas.block_i import (
    InventoryOptimizerIn, StockoutRiskIn, SupplierRiskIn,
    StaffingOptimizerIn, DeliveryRoutingIn, RoutingStop,
)
from app.schemas.block_j import (
    TransactionAnomalyIn, MerchantFraudIn, AMLPatternIn,
    SyntheticIdentityIn, ApplicationFraudIn,
)


# ── Profile ────────────────────────────────────────────────────────────────────

class ChatProfile(BaseModel):
    """Mirrors `frontend/src/lib/chat/profile.ts` `BusinessProfile`.

    All fields have defaults from frontend `DEFAULT_PROFILE` so the LLM can
    work with any subset the user has provided so far.
    """
    region_id: str = "tashkent-01"
    region_label: str = "Toshkent — Yunusobod"
    population: int = 320_000
    avg_income: float = 720.0
    mcc_code: str = "5812"
    mcc_label: str = "Restoran / Ovqatlanish"
    niche: str = "food"

    lat: float = 41.3111
    lon: float = 69.2797
    radius_m: int = 500
    walk_minutes: int = 10
    facade_direction_deg: float = 180.0

    monthly_revenue_estimate: float = 15_000.0
    monthly_fixed_costs: float = 6_000.0
    monthly_rent: float = 1_800.0
    initial_investment: float = 50_000.0
    business_age_months: int = 0
    owner_experience_years: float = 3.0
    owner_credit_history_score: float = 680.0
    collateral_value: float = 25_000.0

    cogs_pct: float = 40.0
    avg_transaction_value: float = 15.0
    monthly_transactions: int = 1_000
    customer_acquisition_cost: float = 5.0
    monthly_churn_rate_pct: float = 5.0
    gross_margin_pct: float = 60.0
    discount_rate_annual_pct: float = 12.0
    horizon_months: int = 24
    growth_rate_monthly_pct: float = 2.0

    requested_loan_amount: float = 30_000.0
    loan_term_months: int = 36
    interest_rate_annual_pct: float = 18.0
    existing_debt_monthly: float = 0.0


# ── Helpers (mirror frontend) ──────────────────────────────────────────────────

def _competitors_for(pop: int) -> int:
    return max(3, round(pop / 6_000))


def _live_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ── Per-model builders ─────────────────────────────────────────────────────────

# Block A — Market Analysis
def _b_a1(p: ChatProfile) -> MarketSizingIn:
    return MarketSizingIn(
        region_id=p.region_id, mcc_code=p.mcc_code,
        population=p.population, avg_income=p.avg_income, niche=p.niche,
    )


def _b_a2(p: ChatProfile) -> GapAnalysisIn:
    return GapAnalysisIn(
        region_id=p.region_id, mcc_code=p.mcc_code,
        normative_density=1.5,
        actual_count=max(1, round(p.population / 5000)),
        population=p.population,
    )


def _b_a3(p: ChatProfile) -> SaturationIndexIn:
    return SaturationIndexIn(
        region_id=p.region_id, mcc_code=p.mcc_code,
        competitor_count=_competitors_for(p.population),
        population=p.population,
        avg_revenue_per_outlet=max(1.0, p.monthly_revenue_estimate * 12),
    )


def _b_a4(p: ChatProfile) -> WalletShareIn:
    return WalletShareIn(
        region_id=p.region_id, mcc_code=p.mcc_code,
        population=p.population,
        avg_monthly_spend=max(1.0, p.avg_income * 0.6),
        competitor_count=_competitors_for(p.population),
    )


def _b_a5(p: ChatProfile) -> NicheOpportunityIn:
    return NicheOpportunityIn(
        region_id=p.region_id, mcc_code=p.mcc_code,
        population=p.population, avg_income=p.avg_income,
        competitor_count=_competitors_for(p.population),
        growth_rate_pct=8.0,
    )


def _b_a6(p: ChatProfile) -> CrossNicheIn:
    adjacent = [m for m in ("5814", "5411", "5999") if m != p.mcc_code]
    return CrossNicheIn(
        new_mcc_code=p.mcc_code,
        location_lat=p.lat, location_lon=p.lon,
        radius_m=p.radius_m,
        adjacent_mcc_codes=adjacent,
    )


# Block B — Forecasting
def _b_b1(p: ChatProfile) -> DemandForecastIn:
    return DemandForecastIn(
        region_id=p.region_id, mcc_code=p.mcc_code,
        horizon_months=max(1, min(36, p.horizon_months)),
        base_monthly_revenue=max(1.0, p.monthly_revenue_estimate),
    )


def _b_b2(p: ChatProfile) -> SeasonalityIn:
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    if year < 2020:
        year = 2026
    if year > 2030:
        year = 2030
    return SeasonalityIn(mcc_code=p.mcc_code, region_id=p.region_id, year=year)


def _b_b3(p: ChatProfile) -> PopulationDynamicsIn:
    return PopulationDynamicsIn(region_id=p.region_id, horizon_years=5)


def _b_b4(p: ChatProfile) -> IncomeTrendIn:
    return IncomeTrendIn(
        region_id=p.region_id,
        horizon_months=max(3, min(36, p.horizon_months)),
        current_avg_income=max(1.0, p.avg_income),
    )


def _b_b5(p: ChatProfile) -> MCCTrendIn:
    return MCCTrendIn(mcc_code=p.mcc_code, region_id=p.region_id, lookback_months=24)


def _b_b6(p: ChatProfile) -> BusinessRegistrationIn:
    return BusinessRegistrationIn(
        region_id=p.region_id, mcc_code=p.mcc_code,
        horizon_months=max(3, min(24, p.horizon_months)),
    )


# Block C — Location
def _b_c1(p: ChatProfile) -> LocationScoreIn:
    return LocationScoreIn(lat=p.lat, lon=p.lon, mcc_code=p.mcc_code, radius_m=p.radius_m)


def _b_c2(p: ChatProfile) -> TrafficScoringIn:
    radius = min(1000, max(50, p.radius_m))
    return TrafficScoringIn(lat=p.lat, lon=p.lon, radius_m=radius)


def _b_c3(p: ChatProfile) -> IsochroneDemandIn:
    # Frontend passes a single int; schema expects list[int].
    return IsochroneDemandIn(
        lat=p.lat, lon=p.lon,
        walk_minutes=[max(1, p.walk_minutes)],
        mcc_code=p.mcc_code,
    )


def _b_c4(p: ChatProfile) -> StreetVitalityIn:
    radius = min(1000, max(50, p.radius_m))
    return StreetVitalityIn(lat=p.lat, lon=p.lon, radius_m=radius)


def _b_c5(p: ChatProfile) -> AnchorEffectIn:
    return AnchorEffectIn(lat=p.lat, lon=p.lon, radius_m=p.radius_m)


def _b_c6(p: ChatProfile) -> VisibilityScoreIn:
    deg = p.facade_direction_deg % 360
    return VisibilityScoreIn(lat=p.lat, lon=p.lon, facade_direction_deg=deg)


# Block D — Financial
def _b_d1(p: ChatProfile) -> ViabilityCheckIn:
    return ViabilityCheckIn(
        mcc_code=p.mcc_code, region_id=p.region_id,
        monthly_revenue_estimate=max(1.0, p.monthly_revenue_estimate),
        monthly_fixed_costs=p.monthly_fixed_costs,
        initial_investment=p.initial_investment,
        monthly_rent=p.monthly_rent,
    )


def _b_d2(p: ChatProfile) -> UnitEconomicsIn:
    return UnitEconomicsIn(
        mcc_code=p.mcc_code,
        avg_transaction_value=max(0.01, p.avg_transaction_value),
        monthly_transactions=max(1, p.monthly_transactions),
        customer_acquisition_cost=p.customer_acquisition_cost,
        monthly_churn_rate_pct=max(0.0, min(100.0, p.monthly_churn_rate_pct)),
        gross_margin_pct=max(0.0, min(100.0, p.gross_margin_pct)),
    )


def _b_d3(p: ChatProfile) -> ROIEstimatorIn:
    net = max(100.0, p.monthly_revenue_estimate - p.monthly_fixed_costs - p.monthly_rent)
    horizon_years = max(1, min(10, round(p.horizon_months / 12)))
    return ROIEstimatorIn(
        initial_investment=max(1.0, p.initial_investment),
        monthly_net_cash_flow=net,
        discount_rate_annual_pct=max(0.0, min(100.0, p.discount_rate_annual_pct)),
        horizon_years=horizon_years,
    )


def _b_d4(p: ChatProfile) -> RentalBurdenIn:
    return RentalBurdenIn(
        mcc_code=p.mcc_code,
        monthly_revenue_estimate=max(1.0, p.monthly_revenue_estimate),
        monthly_rent=max(1.0, p.monthly_rent),
    )


def _b_d5(p: ChatProfile) -> CashFlowSimIn:
    return CashFlowSimIn(
        mcc_code=p.mcc_code, region_id=p.region_id,
        initial_investment=p.initial_investment,
        monthly_revenue_base=max(1.0, p.monthly_revenue_estimate),
        monthly_fixed_costs=p.monthly_fixed_costs,
        cogs_pct=max(0.0, min(100.0, p.cogs_pct)),
        growth_rate_monthly_pct=p.growth_rate_monthly_pct,
        horizon_months=max(6, min(36, p.horizon_months)),
    )


def _b_d6(p: ChatProfile) -> COGSMarginIn:
    return COGSMarginIn(
        mcc_code=p.mcc_code,
        monthly_revenue=max(1.0, p.monthly_revenue_estimate),
        region_id=p.region_id,
    )


# Block E — Competition
def _b_e1(p: ChatProfile) -> CompetitorIntelIn:
    return CompetitorIntelIn(lat=p.lat, lon=p.lon, mcc_code=p.mcc_code)


def _b_e2(p: ChatProfile) -> ChurnPredictionIn:
    return ChurnPredictionIn(
        mcc_code=p.mcc_code, region_id=p.region_id,
        monthly_revenue=max(1.0, p.monthly_revenue_estimate),
        initial_investment=max(1.0, p.initial_investment),
        owner_experience_years=p.owner_experience_years,
        location_score=70.0,
        competition_count=_competitors_for(p.population),
    )


def _b_e3(p: ChatProfile) -> RegulatoryRiskIn:
    return RegulatoryRiskIn(
        mcc_code=p.mcc_code, region_id=p.region_id,
        business_age_months=max(0, p.business_age_months),
    )


def _b_e4(p: ChatProfile) -> EntryBarrierIn:
    return EntryBarrierIn(
        mcc_code=p.mcc_code, region_id=p.region_id,
        initial_investment=max(1.0, p.initial_investment),
    )


def _b_e5(p: ChatProfile) -> PricePressureIn:
    target = max(0.01, p.avg_transaction_value)
    return PricePressureIn(
        mcc_code=p.mcc_code, region_id=p.region_id,
        target_price=target, competitor_avg_price=target * 1.1,
    )


# Block F — Credit
def _b_f1(p: ChatProfile) -> CreditRiskIn:
    return CreditRiskIn(
        customer_id=_live_id("cust"),
        mcc_code=p.mcc_code, region_id=p.region_id,
        lat=p.lat, lon=p.lon,
        monthly_revenue_estimate=max(1.0, p.monthly_revenue_estimate),
        requested_loan_amount=max(1.0, p.requested_loan_amount),
        business_age_months=max(0, p.business_age_months),
        owner_credit_history_score=max(300.0, min(850.0, p.owner_credit_history_score)),
        collateral_value=max(0.0, p.collateral_value),
    )


def _b_f2(p: ChatProfile) -> LoanSizingIn:
    net = max(100.0, p.monthly_revenue_estimate - p.monthly_fixed_costs - p.monthly_rent)
    return LoanSizingIn(
        monthly_net_cashflow=net,
        monthly_revenue=max(1.0, p.monthly_revenue_estimate),
        existing_debt_monthly=max(0.0, p.existing_debt_monthly),
        loan_term_months=max(6, min(120, p.loan_term_months)),
        interest_rate_annual_pct=max(0.0, min(100.0, p.interest_rate_annual_pct)),
    )


def _b_f3(p: ChatProfile) -> DTIPredictorIn:
    return DTIPredictorIn(
        mcc_code=p.mcc_code, region_id=p.region_id,
        initial_monthly_revenue=max(1.0, p.monthly_revenue_estimate),
        proposed_loan_amount=max(1.0, p.requested_loan_amount),
        loan_term_months=max(6, min(120, p.loan_term_months)),
        interest_rate_annual_pct=p.interest_rate_annual_pct,
    )


def _b_f4(p: ChatProfile) -> NPLWarningIn:
    return NPLWarningIn(
        customer_id=_live_id("cust"),
        loan_id=_live_id("loan"),
        months_since_disbursement=6,
        payment_delays_count=0,
        revenue_trend_3m_pct=p.growth_rate_monthly_pct * 3,
        current_dti=0.35,
        location_score=70.0,
    )


def _b_f5(p: ChatProfile) -> ProductRecommenderIn:
    return ProductRecommenderIn(
        customer_id=_live_id("cust"),
        mcc_code=p.mcc_code,
        monthly_revenue=max(1.0, p.monthly_revenue_estimate),
        business_age_months=max(0, p.business_age_months),
        existing_products=[],
        credit_score=max(300.0, min(1000.0, p.owner_credit_history_score)),
    )


# Block G — Social
def _b_g1(p: ChatProfile) -> CustomerProfilerIn:
    return CustomerProfilerIn(lat=p.lat, lon=p.lon, radius_m=p.radius_m, mcc_code=p.mcc_code)


def _b_g2(p: ChatProfile) -> DayPopulationIn:
    return DayPopulationIn(
        lat=p.lat, lon=p.lon, radius_m=p.radius_m,
        hour_of_day=14, day_of_week=3,
    )


def _b_g3(p: ChatProfile) -> BehaviorClassifierIn:
    return BehaviorClassifierIn(lat=p.lat, lon=p.lon, radius_m=p.radius_m, mcc_code=p.mcc_code)


def _b_g4(p: ChatProfile) -> BrandAffinityIn:
    return BrandAffinityIn(lat=p.lat, lon=p.lon, radius_m=p.radius_m, mcc_code=p.mcc_code)


def _b_g5(p: ChatProfile) -> SpendingPowerIn:
    radius = max(200, min(5000, p.radius_m * 2))
    return SpendingPowerIn(lat=p.lat, lon=p.lon, radius_m=radius)


# Block H — Marketing
def _b_h1(p: ChatProfile) -> CACPredictorIn:
    return CACPredictorIn(
        channel="paid_search", region_id=p.region_id,
        monthly_budget=max(500.0, p.monthly_revenue_estimate * 0.10),
        industry_mcc=p.mcc_code,
        target_segment="consumer",
        historical_cac=max(0.0, p.customer_acquisition_cost),
        competition_intensity=0.5,
    )


def _b_h2(p: ChatProfile) -> LTVCACRatioIn:
    return LTVCACRatioIn(
        arpu_monthly=max(1.0, p.avg_transaction_value),
        gross_margin_pct=max(0.0, min(1.0, p.gross_margin_pct / 100)),
        monthly_churn_rate=max(0.005, min(1.0, p.monthly_churn_rate_pct / 100)),
        discount_rate_annual=max(0.0, min(1.0, p.discount_rate_annual_pct / 100)),
        cac=max(1.0, p.customer_acquisition_cost),
    )


def _b_h3(p: ChatProfile) -> ChannelAttributionIn:
    return ChannelAttributionIn(
        journey_id=_live_id("jrn"),
        touchpoints=["social", "paid_search", "email", "organic"],
        conversion_value=max(10.0, p.avg_transaction_value),
    )


def _b_h4(p: ChatProfile) -> PromoUpliftIn:
    atv = max(0.01, p.avg_transaction_value)
    return PromoUpliftIn(
        customer_id=_live_id("cust"),
        promo_type="discount",
        promo_value=max(1.0, atv * 0.15),
        customer_recency_days=30,
        customer_frequency_30d=4,
        customer_monetary_30d=atv * 4,
        historical_response_rate=0.12,
    )


def _b_h5(p: ChatProfile) -> OptimalPricingIn:
    atv = max(1.0, p.avg_transaction_value)
    return OptimalPricingIn(
        product_id=_live_id("prod"),
        current_price=atv,
        current_units_sold=max(1.0, float(p.monthly_transactions)),
        unit_cost=max(0.0, atv * (p.cogs_pct / 100)),
        elasticity_estimate=-1.5,
    )


def _b_h6(p: ChatProfile) -> LookalikeAudienceIn:
    atv = max(0.01, p.avg_transaction_value)
    monthly_spend_seed = atv * max(1, p.monthly_transactions / 30)
    seed = {"avg_income": float(p.avg_income), "monthly_spend": float(monthly_spend_seed), "frequency": 8.0}
    candidates = [
        {
            "customer_id": f"cand-{i}",
            "avg_income": float(p.avg_income) + i * 20,
            "monthly_spend": float(monthly_spend_seed) * (0.6 + i * 0.05),
            "frequency": float(3 + (i % 6)),
        }
        for i in range(12)
    ]
    return LookalikeAudienceIn(
        seed_customer_features=seed,
        candidate_pool=candidates,
        top_k=5,
    )


# Block I — Operations
def _b_i1(p: ChatProfile) -> InventoryOptimizerIn:
    daily_demand = p.monthly_transactions / 30
    return InventoryOptimizerIn(
        sku_id=_live_id("sku"),
        annual_demand=max(50.0, float(p.monthly_transactions) * 12),
        unit_cost=max(1.0, p.avg_transaction_value * (p.cogs_pct / 100)),
        ordering_cost=50.0,
        holding_cost_pct=0.20,
        lead_time_days=14,
        demand_std_daily=max(0.0, daily_demand * 0.2),
        service_level=0.95,
    )


def _b_i2(p: ChatProfile) -> StockoutRiskIn:
    daily_demand = p.monthly_transactions / 30
    return StockoutRiskIn(
        sku_id=_live_id("sku"),
        on_hand_units=max(1.0, round(daily_demand * 14)),
        on_order_units=0,
        daily_demand_mean=max(0.1, daily_demand),
        daily_demand_std=max(0.05, daily_demand * 0.2),
        lead_time_days_mean=14,
        lead_time_days_std=2,
        horizon_days=30,
    )


def _b_i3(p: ChatProfile) -> SupplierRiskIn:
    return SupplierRiskIn(
        supplier_id=_live_id("sup"),
        months_active=24,
        on_time_delivery_rate=0.92,
        quality_defect_rate=0.02,
        payment_terms_days=30,
        payment_delay_avg_days=3.0,
        revenue_concentration_pct=0.15,
        single_source_flag=False,
        geopolitical_risk=0.30,
    )


def _b_i4(p: ChatProfile) -> StaffingOptimizerIn:
    import math
    peak = p.monthly_transactions / 30
    hourly = []
    for h in range(24):
        if 8 <= h <= 22:
            multiplier = math.exp(-((h - 13) ** 2) / 18) * 4
            hourly.append(max(0.0, round(peak * multiplier)))
        else:
            hourly.append(0.0)
    return StaffingOptimizerIn(
        location_id=_live_id("loc"),
        hourly_demand=hourly,
        units_per_staff_hour=10.0,
        min_staff_per_open_hour=1,
        max_staff=20,
        hourly_wage=5.0,
        open_hour=8,
        close_hour=22,
    )


def _b_i5(p: ChatProfile) -> DeliveryRoutingIn:
    # Six stops arranged in a small fixed pattern around the depot for deterministic input.
    offsets = [
        (0.010, 0.000), (0.000, 0.010), (-0.010, 0.000),
        (0.000, -0.010), (0.008, 0.008), (-0.008, -0.008),
    ]
    stops = [
        RoutingStop(stop_id=f"stop-{i}", lat=p.lat + dx, lon=p.lon + dy, demand=1.0 + i * 0.5)
        for i, (dx, dy) in enumerate(offsets)
    ]
    return DeliveryRoutingIn(
        depot_lat=p.lat, depot_lon=p.lon,
        stops=stops, vehicle_capacity=100.0, n_vehicles=2,
    )


# Block J — Fraud
def _b_j1(p: ChatProfile) -> TransactionAnomalyIn:
    return TransactionAnomalyIn(
        customer_id=_live_id("cust"),
        transaction_id=_live_id("tx"),
        amount=max(1.0, p.avg_transaction_value),
        mcc_code=p.mcc_code,
        txn_count_last_24h=3,
        txn_count_last_7d=18,
        avg_amount_last_30d=max(0.0, p.avg_transaction_value),
        distinct_merchants_last_24h=2,
        is_foreign=False,
        is_cnp=False,
        hour_of_day=14,
    )


def _b_j2(p: ChatProfile) -> MerchantFraudIn:
    return MerchantFraudIn(
        merchant_id=_live_id("mer"),
        mcc_code=p.mcc_code,
        months_active=max(0, p.business_age_months),
        chargeback_rate_30d=0.005,
        refund_rate_30d=0.02,
        avg_ticket_size=max(1.0, p.avg_transaction_value),
        txn_velocity_per_day=max(0.0, p.monthly_transactions / 30),
        pct_cnp_transactions=0.10,
        pct_foreign_cards=0.02,
        prior_complaints_count=0,
    )


def _b_j3(p: ChatProfile) -> AMLPatternIn:
    return AMLPatternIn(
        customer_id=_live_id("cust"),
        cash_deposits_last_7d=2,
        cash_amount_last_7d=4500.0,
        structuring_threshold=10000.0,
        near_threshold_deposits_30d=0,
        rapid_in_out_count_30d=0,
        distinct_counterparties_30d=6,
        cross_border_count_30d=0,
        high_risk_jurisdiction_count=0,
    )


def _b_j4(p: ChatProfile) -> SyntheticIdentityIn:
    return SyntheticIdentityIn(
        applicant_id=_live_id("app"),
        credit_file_age_months=max(0, int(p.owner_experience_years * 12)),
        credit_inquiries_last_6m=1,
        address_changes_last_24m=0,
        ssn_age_norm=0.95,
        phone_tenure_months=36,
        email_tenure_months=48,
        distinct_names_at_address=1,
        employer_verifiable=True,
    )


def _b_j5(p: ChatProfile) -> ApplicationFraudIn:
    annual_income = max(100.0, p.avg_income * 12)
    return ApplicationFraudIn(
        application_id=_live_id("app"),
        applications_last_24h=1,
        applications_last_30d=1,
        device_seen_count_30d=1,
        ip_seen_count_30d=1,
        declared_income=annual_income,
        bureau_income_estimate=annual_income * 0.95,
        document_quality_score=0.92,
        velocity_score=0.10,
        geolocation_mismatch=False,
    )


# ── Dispatcher ─────────────────────────────────────────────────────────────────

_BUILDERS: dict[str, Callable[[ChatProfile], BaseModel]] = {
    "M-A1": _b_a1, "M-A2": _b_a2, "M-A3": _b_a3, "M-A4": _b_a4, "M-A5": _b_a5, "M-A6": _b_a6,
    "M-B1": _b_b1, "M-B2": _b_b2, "M-B3": _b_b3, "M-B4": _b_b4, "M-B5": _b_b5, "M-B6": _b_b6,
    "M-C1": _b_c1, "M-C2": _b_c2, "M-C3": _b_c3, "M-C4": _b_c4, "M-C5": _b_c5, "M-C6": _b_c6,
    "M-D1": _b_d1, "M-D2": _b_d2, "M-D3": _b_d3, "M-D4": _b_d4, "M-D5": _b_d5, "M-D6": _b_d6,
    "M-E1": _b_e1, "M-E2": _b_e2, "M-E3": _b_e3, "M-E4": _b_e4, "M-E5": _b_e5,
    "M-F1": _b_f1, "M-F2": _b_f2, "M-F3": _b_f3, "M-F4": _b_f4, "M-F5": _b_f5,
    "M-G1": _b_g1, "M-G2": _b_g2, "M-G3": _b_g3, "M-G4": _b_g4, "M-G5": _b_g5,
    "M-H1": _b_h1, "M-H2": _b_h2, "M-H3": _b_h3, "M-H4": _b_h4, "M-H5": _b_h5, "M-H6": _b_h6,
    "M-I1": _b_i1, "M-I2": _b_i2, "M-I3": _b_i3, "M-I4": _b_i4, "M-I5": _b_i5,
    "M-J1": _b_j1, "M-J2": _b_j2, "M-J3": _b_j3, "M-J4": _b_j4, "M-J5": _b_j5,
}


def build(model_id: str, profile: ChatProfile) -> BaseModel:
    """Build a Pydantic input instance for `model_id` from `profile`.

    Raises KeyError if `model_id` is not supported.
    """
    builder = _BUILDERS.get(model_id)
    if builder is None:
        raise KeyError(f"No input builder for model_id={model_id!r}")
    return builder(profile)


def supported_model_ids() -> list[str]:
    return sorted(_BUILDERS.keys())
