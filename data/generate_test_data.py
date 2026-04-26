"""
Generate 1000-row test datasets for each of the 7 model blocks.
Output: data/test/block_X.csv  (one file per block)

Run: python data/generate_test_data.py
"""

import uuid
import json
import numpy as np
import pandas as pd
from pathlib import Path

OUT = Path(__file__).parent / "test"
OUT.mkdir(exist_ok=True)

RNG = np.random.default_rng(42)
N = 1000

# ── Uzbekistan geography ──────────────────────────────────────────────────────
REGIONS = [
    "tashkent-01", "tashkent-02", "samarkand-01", "bukhara-01",
    "namangan-01", "fergana-01", "andijan-01", "nukus-01",
    "termez-01", "jizzakh-01", "gulistan-01", "navoiy-01",
]

# Bounding boxes (lat_min, lat_max, lon_min, lon_max) per region
REGION_BBOX = {
    "tashkent-01":  (41.20, 41.40, 69.15, 69.40),
    "tashkent-02":  (41.10, 41.25, 69.30, 69.60),
    "samarkand-01": (39.60, 39.75, 66.90, 67.15),
    "bukhara-01":   (39.72, 39.82, 64.38, 64.52),
    "namangan-01":  (40.95, 41.05, 71.60, 71.75),
    "fergana-01":   (40.35, 40.45, 71.75, 71.90),
    "andijan-01":   (40.72, 40.82, 72.32, 72.45),
    "nukus-01":     (42.42, 42.55, 59.55, 59.68),
    "termez-01":    (37.20, 37.30, 67.25, 67.38),
    "jizzakh-01":   (40.10, 40.20, 67.82, 67.95),
    "gulistan-01":  (40.47, 40.57, 68.73, 68.87),
    "navoiy-01":    (40.08, 40.18, 65.35, 65.50),
}

MCC_CODES = [
    "5812", "5814", "5411", "5912", "7011",
    "5651", "7372", "5940", "5999", "5047",
    "5621", "5712", "7011", "5734", "5511",
]

MCC_NICHES = {
    "5812": "restaurant", "5814": "fast_food", "5411": "grocery",
    "5912": "pharmacy",   "7011": "hotel",     "5651": "clothing",
    "7372": "software",   "5940": "sports",    "5999": "retail",
    "5047": "medical_equipment", "5621": "womens_clothing",
    "5712": "furniture",  "5734": "electronics", "5511": "auto_dealer",
}

ADJACENT_MCC_MAP = {
    "5812": ["5814", "5411", "5999"],
    "5814": ["5812", "5411"],
    "5411": ["5912", "5999", "5812"],
    "5912": ["5411", "5047"],
    "7011": ["5812", "5814"],
    "5651": ["5621", "5712"],
    "7372": ["5734"],
    "5940": ["5651", "5999"],
    "5999": ["5411", "5651"],
    "5047": ["5912"],
    "5621": ["5651", "5712"],
    "5712": ["5651", "5999"],
    "5734": ["7372", "5999"],
    "5511": ["5940", "5999"],
}


def pick_region():
    return RNG.choice(REGIONS, N)


def pick_mcc():
    return RNG.choice(MCC_CODES, N)


def lat_lon_for_regions(regions):
    lats, lons = [], []
    for r in regions:
        bb = REGION_BBOX.get(r, (39.0, 42.0, 60.0, 73.0))
        lats.append(RNG.uniform(bb[0], bb[1]))
        lons.append(RNG.uniform(bb[2], bb[3]))
    return np.array(lats), np.array(lons)


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK A — Market Analysis & Capacity
# ─────────────────────────────────────────────────────────────────────────────
def gen_block_a():
    regions = pick_region()
    mccs    = pick_mcc()
    lats, lons = lat_lon_for_regions(regions)

    population             = RNG.integers(5_000, 500_000, N)
    avg_income             = RNG.uniform(150, 1_200, N).round(2)
    normative_density      = RNG.uniform(0.5, 8.0, N).round(2)   # outlets per 10k pop
    actual_count           = RNG.integers(0, 80, N)
    competitor_count       = RNG.integers(0, 60, N)
    avg_revenue_per_outlet = RNG.uniform(1_000, 50_000, N).round(2)
    avg_monthly_spend      = RNG.uniform(50, 800, N).round(2)
    growth_rate_pct        = RNG.uniform(-5, 25, N).round(2)
    radius_m               = RNG.choice([200, 300, 500, 750, 1000], N)

    adjacent_mccs = []
    for m in mccs:
        pool = ADJACENT_MCC_MAP.get(m, ["5999"])
        k = min(RNG.integers(1, 4), len(pool))
        adjacent_mccs.append(",".join(RNG.choice(pool, size=k, replace=False).tolist()))

    df = pd.DataFrame({
        "region_id":              regions,
        "mcc_code":               mccs,
        "niche":                  [MCC_NICHES.get(m, "retail") for m in mccs],
        "population":             population,
        "avg_income":             avg_income,
        "normative_density":      normative_density,
        "actual_count":           actual_count,
        "competitor_count":       competitor_count,
        "avg_revenue_per_outlet": avg_revenue_per_outlet,
        "avg_monthly_spend":      avg_monthly_spend,
        "growth_rate_pct":        growth_rate_pct,
        "location_lat":           lats.round(6),
        "location_lon":           lons.round(6),
        "radius_m":               radius_m,
        "adjacent_mcc_codes":     adjacent_mccs,
    })
    df.to_csv(OUT / "block_a.csv", index=False)
    print(f"block_a.csv — {len(df)} rows")


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK B — Forecasting & Demand
# ─────────────────────────────────────────────────────────────────────────────
def gen_block_b():
    regions = pick_region()
    mccs    = pick_mcc()

    horizon_months       = RNG.integers(1, 37, N)
    base_monthly_revenue = RNG.uniform(500, 100_000, N).round(2)
    year                 = RNG.integers(2024, 2031, N)
    horizon_years        = RNG.integers(1, 21, N)
    current_avg_income   = RNG.uniform(150, 1_200, N).round(2)
    lookback_months      = RNG.integers(6, 61, N)

    df = pd.DataFrame({
        "region_id":           regions,
        "mcc_code":            mccs,
        "horizon_months":      horizon_months,
        "base_monthly_revenue": base_monthly_revenue,
        "year":                year,
        "horizon_years":       horizon_years,
        "current_avg_income":  current_avg_income,
        "lookback_months":     lookback_months,
    })
    df.to_csv(OUT / "block_b.csv", index=False)
    print(f"block_b.csv — {len(df)} rows")


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK C — Location Assessment & Traffic
# ─────────────────────────────────────────────────────────────────────────────
def gen_block_c():
    regions = pick_region()
    mccs    = pick_mcc()
    lats, lons = lat_lon_for_regions(regions)

    radius_m              = RNG.choice([100, 200, 300, 500, 750, 1000, 2000], N)
    walk_minutes_5        = RNG.choice([0, 1], N, p=[0.3, 0.7])   # include 5-min iso?
    walk_minutes_10       = np.ones(N, dtype=int)                  # always include 10-min
    facade_direction_deg  = RNG.uniform(0, 360, N).round(1)

    # walk_minutes stored as JSON list
    walk_minutes = [
        json.dumps([5, 10] if w5 else [10])
        for w5 in walk_minutes_5
    ]

    df = pd.DataFrame({
        "region_id":           regions,
        "mcc_code":            mccs,
        "lat":                 lats.round(6),
        "lon":                 lons.round(6),
        "radius_m":            radius_m,
        "walk_minutes":        walk_minutes,
        "facade_direction_deg": facade_direction_deg,
    })
    df.to_csv(OUT / "block_c.csv", index=False)
    print(f"block_c.csv — {len(df)} rows")


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK D — Financial Viability
# ─────────────────────────────────────────────────────────────────────────────
def gen_block_d():
    regions = pick_region()
    mccs    = pick_mcc()

    monthly_revenue_estimate = RNG.uniform(1_000, 150_000, N).round(2)
    monthly_fixed_costs      = (monthly_revenue_estimate * RNG.uniform(0.20, 0.65, N)).round(2)
    initial_investment       = RNG.uniform(2_000, 500_000, N).round(2)
    monthly_rent             = RNG.uniform(100, 8_000, N).round(2)

    # Unit economics
    avg_transaction_value    = RNG.uniform(3, 500, N).round(2)
    monthly_transactions     = RNG.integers(10, 10_000, N)
    customer_acquisition_cost = RNG.uniform(5, 300, N).round(2)
    monthly_churn_rate_pct   = RNG.uniform(0.5, 25, N).round(2)
    gross_margin_pct         = RNG.uniform(10, 80, N).round(2)

    # ROI
    monthly_net_cash_flow    = (monthly_revenue_estimate * RNG.uniform(-0.1, 0.35, N)).round(2)
    discount_rate_annual_pct = RNG.uniform(8, 30, N).round(2)
    horizon_years            = RNG.integers(1, 11, N)

    # Cash flow sim
    cogs_pct                 = RNG.uniform(15, 70, N).round(2)
    growth_rate_monthly_pct  = RNG.uniform(-2, 5, N).round(2)
    horizon_months           = RNG.integers(6, 37, N)

    df = pd.DataFrame({
        "region_id":               regions,
        "mcc_code":                mccs,
        "monthly_revenue_estimate": monthly_revenue_estimate,
        "monthly_fixed_costs":     monthly_fixed_costs,
        "initial_investment":      initial_investment,
        "monthly_rent":            monthly_rent,
        "avg_transaction_value":   avg_transaction_value,
        "monthly_transactions":    monthly_transactions,
        "customer_acquisition_cost": customer_acquisition_cost,
        "monthly_churn_rate_pct":  monthly_churn_rate_pct,
        "gross_margin_pct":        gross_margin_pct,
        "monthly_net_cash_flow":   monthly_net_cash_flow,
        "monthly_revenue":         monthly_revenue_estimate,   # alias for D6
        "discount_rate_annual_pct": discount_rate_annual_pct,
        "horizon_years":           horizon_years,
        "cogs_pct":                cogs_pct,
        "growth_rate_monthly_pct": growth_rate_monthly_pct,
        "horizon_months":          horizon_months,
    })
    df.to_csv(OUT / "block_d.csv", index=False)
    print(f"block_d.csv — {len(df)} rows")


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK E — Competition & Risks
# ─────────────────────────────────────────────────────────────────────────────
def gen_block_e():
    regions = pick_region()
    mccs    = pick_mcc()
    lats, lons = lat_lon_for_regions(regions)

    monthly_revenue       = RNG.uniform(500, 100_000, N).round(2)
    initial_investment    = RNG.uniform(2_000, 300_000, N).round(2)
    owner_experience_years = RNG.uniform(0, 30, N).round(1)
    location_score        = RNG.uniform(0, 100, N).round(1)
    competition_count     = RNG.integers(0, 50, N)
    business_age_months   = RNG.integers(0, 120, N)
    target_price          = RNG.uniform(1, 500, N).round(2)
    # competitor avg price ±30% of target
    competitor_avg_price  = (target_price * RNG.uniform(0.7, 1.3, N)).round(2)
    radius_300m           = RNG.choice([True, False], N, p=[0.8, 0.2])
    radius_1km            = np.ones(N, dtype=bool)

    df = pd.DataFrame({
        "region_id":             regions,
        "mcc_code":              mccs,
        "lat":                   lats.round(6),
        "lon":                   lons.round(6),
        "monthly_revenue":       monthly_revenue,
        "initial_investment":    initial_investment,
        "owner_experience_years": owner_experience_years,
        "location_score":        location_score,
        "competition_count":     competition_count,
        "business_age_months":   business_age_months,
        "target_price":          target_price,
        "competitor_avg_price":  competitor_avg_price,
        "radius_300m":           radius_300m,
        "radius_1km":            radius_1km,
    })
    df.to_csv(OUT / "block_e.csv", index=False)
    print(f"block_e.csv — {len(df)} rows")


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK F — Credit & Banking Products
# ─────────────────────────────────────────────────────────────────────────────
def gen_block_f():
    regions = pick_region()
    mccs    = pick_mcc()
    lats, lons = lat_lon_for_regions(regions)

    customer_ids                 = [f"CUST-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]
    loan_ids                     = [f"LOAN-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]

    monthly_revenue_estimate     = RNG.uniform(500, 100_000, N).round(2)
    requested_loan_amount        = (monthly_revenue_estimate * RNG.uniform(3, 36, N)).round(2)
    business_age_months          = RNG.integers(0, 120, N)
    owner_credit_history_score   = RNG.uniform(300, 850, N).round(0)
    collateral_value             = (requested_loan_amount * RNG.uniform(0, 2.5, N)).round(2)

    monthly_net_cashflow         = (monthly_revenue_estimate * RNG.uniform(-0.05, 0.40, N)).round(2)
    existing_debt_monthly        = RNG.uniform(0, 5_000, N).round(2)
    loan_term_months             = RNG.choice([6, 12, 18, 24, 36, 48, 60, 84, 120], N)
    interest_rate_annual_pct     = RNG.uniform(12, 36, N).round(2)

    months_since_disbursement    = RNG.integers(0, 60, N)
    payment_delays_count         = RNG.integers(0, 10, N)
    revenue_trend_3m_pct         = RNG.uniform(-30, 30, N).round(2)
    current_dti                  = RNG.uniform(0.05, 0.90, N).round(3)

    credit_score                 = RNG.uniform(300, 1000, N).round(0)
    existing_products            = [
        json.dumps(
            RNG.choice(
                ["business_loan", "overdraft", "pos_terminal", "deposit"],
                size=RNG.integers(0, 3),
                replace=False
            ).tolist()
        )
        for _ in range(N)
    ]

    proposed_loan_amount         = requested_loan_amount  # alias for F3
    initial_monthly_revenue      = monthly_revenue_estimate  # alias for F3

    df = pd.DataFrame({
        "customer_id":                customer_ids,
        "loan_id":                    loan_ids,
        "region_id":                  regions,
        "mcc_code":                   mccs,
        "lat":                        lats.round(6),
        "lon":                        lons.round(6),
        "monthly_revenue_estimate":   monthly_revenue_estimate,
        "monthly_revenue":            monthly_revenue_estimate,
        "initial_monthly_revenue":    initial_monthly_revenue,
        "requested_loan_amount":      requested_loan_amount,
        "proposed_loan_amount":       proposed_loan_amount,
        "business_age_months":        business_age_months,
        "owner_credit_history_score": owner_credit_history_score,
        "collateral_value":           collateral_value,
        "monthly_net_cashflow":       monthly_net_cashflow,
        "existing_debt_monthly":      existing_debt_monthly,
        "loan_term_months":           loan_term_months,
        "interest_rate_annual_pct":   interest_rate_annual_pct,
        "months_since_disbursement":  months_since_disbursement,
        "payment_delays_count":       payment_delays_count,
        "revenue_trend_3m_pct":       revenue_trend_3m_pct,
        "current_dti":                current_dti,
        "credit_score":               credit_score,
        "existing_products":          existing_products,
    })
    df.to_csv(OUT / "block_f.csv", index=False)
    print(f"block_f.csv — {len(df)} rows")


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK G — Social Profile & Audience
# ─────────────────────────────────────────────────────────────────────────────
def gen_block_g():
    regions = pick_region()
    mccs    = pick_mcc()
    lats, lons = lat_lon_for_regions(regions)

    radius_m    = RNG.choice([100, 200, 300, 500, 750, 1000, 2000, 5000], N)
    hour_of_day = RNG.integers(0, 24, N)
    day_of_week = RNG.integers(0, 7, N)

    df = pd.DataFrame({
        "region_id":  regions,
        "mcc_code":   mccs,
        "lat":        lats.round(6),
        "lon":        lons.round(6),
        "radius_m":   radius_m,
        "hour_of_day": hour_of_day,
        "day_of_week": day_of_week,
    })
    df.to_csv(OUT / "block_g.csv", index=False)
    print(f"block_g.csv — {len(df)} rows")


# ─────────────────────────────────────────────────────────────────────────────
# Block H — Marketing & Customer Acquisition (M-H1 .. M-H6)
# ─────────────────────────────────────────────────────────────────────────────
def gen_block_h():
    customer_ids = [f"CUST-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]
    journey_ids  = [f"JOUR-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]
    product_ids  = [f"PROD-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]

    channels      = RNG.choice(["paid_search", "social", "referral",
                                "display", "email", "organic"], N)
    region_ids    = pick_region()
    monthly_budget = RNG.uniform(500, 100_000, N).round(2)
    industry_mcc  = pick_mcc()
    target_segment = RNG.choice(["smb", "consumer", "enterprise"], N)
    historical_cac = RNG.uniform(0, 200, N).round(2)
    competition_intensity = RNG.uniform(0, 1, N).round(3)

    arpu_monthly       = RNG.uniform(20, 500, N).round(2)
    gross_margin_pct   = RNG.uniform(0.1, 0.85, N).round(3)
    monthly_churn_rate = RNG.uniform(0.005, 0.12, N).round(4)
    discount_rate_annual = RNG.uniform(0.05, 0.15, N).round(3)
    cac                = RNG.uniform(10, 300, N).round(2)

    touchpoints_pool = ["paid_search", "social", "email", "referral",
                        "display", "organic", "direct", "video"]
    touchpoints = [
        json.dumps(list(RNG.choice(touchpoints_pool,
                                   size=RNG.integers(1, 6),
                                   replace=True)))
        for _ in range(N)
    ]
    conversion_value = RNG.uniform(50, 5000, N).round(2)

    promo_type   = RNG.choice(["discount", "cashback", "free_trial", "bundle"], N)
    promo_value  = RNG.uniform(5, 200, N).round(2)
    customer_recency_days = RNG.integers(1, 365, N)
    customer_frequency_30d = RNG.integers(0, 15, N)
    customer_monetary_30d  = RNG.uniform(0, 3000, N).round(2)
    historical_response_rate = RNG.uniform(0.02, 0.40, N).round(3)

    current_price        = RNG.uniform(5, 500, N).round(2)
    current_units_sold   = RNG.uniform(50, 5000, N).round(0)
    unit_cost            = (current_price * RNG.uniform(0.20, 0.70, N)).round(2)
    elasticity_estimate  = -RNG.uniform(0.5, 3.0, N).round(3)

    df = pd.DataFrame({
        "customer_id":              customer_ids,
        "journey_id":               journey_ids,
        "product_id":               product_ids,
        "channel":                  channels,
        "region_id":                region_ids,
        "monthly_budget":           monthly_budget,
        "industry_mcc":             industry_mcc,
        "target_segment":           target_segment,
        "historical_cac":           historical_cac,
        "competition_intensity":    competition_intensity,
        "arpu_monthly":             arpu_monthly,
        "gross_margin_pct":         gross_margin_pct,
        "monthly_churn_rate":       monthly_churn_rate,
        "discount_rate_annual":     discount_rate_annual,
        "cac":                      cac,
        "touchpoints":              touchpoints,
        "conversion_value":         conversion_value,
        "promo_type":               promo_type,
        "promo_value":              promo_value,
        "customer_recency_days":    customer_recency_days,
        "customer_frequency_30d":   customer_frequency_30d,
        "customer_monetary_30d":    customer_monetary_30d,
        "historical_response_rate": historical_response_rate,
        "current_price":            current_price,
        "current_units_sold":       current_units_sold,
        "unit_cost":                unit_cost,
        "elasticity_estimate":      elasticity_estimate,
    })
    df.to_csv(OUT / "block_h.csv", index=False)
    print(f"block_h.csv — {len(df)} rows")


# ─────────────────────────────────────────────────────────────────────────────
# Block I — Operations & Supply Chain (M-I1 .. M-I5)
# ─────────────────────────────────────────────────────────────────────────────
def gen_block_i():
    sku_ids       = [f"SKU-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]
    supplier_ids  = [f"SUP-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]
    location_ids  = [f"LOC-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]

    annual_demand        = RNG.uniform(500, 100_000, N).round(0)
    unit_cost            = RNG.uniform(1, 200, N).round(2)
    ordering_cost        = RNG.uniform(20, 200, N).round(2)
    holding_cost_pct     = RNG.uniform(0.10, 0.30, N).round(3)
    lead_time_days       = RNG.uniform(2, 45, N).round(1)
    demand_std_daily     = RNG.uniform(0, 30, N).round(2)
    service_level        = RNG.uniform(0.85, 0.99, N).round(3)

    on_hand_units        = RNG.uniform(0, 5000, N).round(0)
    on_order_units       = RNG.uniform(0, 5000, N).round(0)
    daily_demand_mean    = RNG.uniform(1, 200, N).round(2)
    daily_demand_std     = RNG.uniform(0, 50, N).round(2)
    lead_time_days_mean  = RNG.uniform(2, 45, N).round(1)
    lead_time_days_std   = RNG.uniform(0, 5, N).round(2)
    horizon_days         = RNG.integers(7, 90, N)

    months_active             = RNG.integers(0, 240, N)
    on_time_delivery_rate     = RNG.uniform(0.5, 1.0, N).round(3)
    quality_defect_rate       = RNG.uniform(0, 0.10, N).round(4)
    payment_terms_days        = RNG.choice([15, 30, 45, 60, 90], N)
    payment_delay_avg_days    = RNG.uniform(0, 30, N).round(1)
    revenue_concentration_pct = RNG.uniform(0.01, 0.80, N).round(3)
    single_source_flag        = RNG.binomial(1, 0.20, N).astype(bool)
    geopolitical_risk         = RNG.uniform(0.05, 0.85, N).round(3)

    hourly_demand = [
        json.dumps((RNG.uniform(0, 80, 24)).round(1).tolist())
        for _ in range(N)
    ]
    units_per_staff_hour = RNG.uniform(5, 25, N).round(2)
    min_staff_per_open_hour = RNG.integers(1, 4, N)
    max_staff = RNG.integers(8, 30, N)
    hourly_wage = RNG.uniform(8, 35, N).round(2)
    open_hour = RNG.integers(6, 11, N)
    close_hour = RNG.integers(19, 24, N)

    # Routing — small synthetic VRP problem per row
    depot_lat = RNG.uniform(40.0, 41.5, N).round(5)
    depot_lon = RNG.uniform(67.0, 71.5, N).round(5)
    stops = [
        json.dumps([
            {
                "stop_id": f"S{i + 1}",
                "lat": float(round(depot_lat[k] + RNG.uniform(-0.05, 0.05), 5)),
                "lon": float(round(depot_lon[k] + RNG.uniform(-0.05, 0.05), 5)),
                "demand": float(round(RNG.uniform(1, 20), 2)),
            }
            for i in range(8)
        ])
        for k in range(N)
    ]
    vehicle_capacity = RNG.uniform(50, 200, N).round(1)
    n_vehicles       = RNG.integers(2, 6, N)

    df = pd.DataFrame({
        "sku_id":                   sku_ids,
        "supplier_id":              supplier_ids,
        "location_id":              location_ids,
        "annual_demand":            annual_demand,
        "unit_cost":                unit_cost,
        "ordering_cost":            ordering_cost,
        "holding_cost_pct":         holding_cost_pct,
        "lead_time_days":           lead_time_days,
        "demand_std_daily":         demand_std_daily,
        "service_level":            service_level,
        "on_hand_units":            on_hand_units,
        "on_order_units":           on_order_units,
        "daily_demand_mean":        daily_demand_mean,
        "daily_demand_std":         daily_demand_std,
        "lead_time_days_mean":      lead_time_days_mean,
        "lead_time_days_std":       lead_time_days_std,
        "horizon_days":             horizon_days,
        "months_active":            months_active,
        "on_time_delivery_rate":    on_time_delivery_rate,
        "quality_defect_rate":      quality_defect_rate,
        "payment_terms_days":       payment_terms_days,
        "payment_delay_avg_days":   payment_delay_avg_days,
        "revenue_concentration_pct": revenue_concentration_pct,
        "single_source_flag":       single_source_flag,
        "geopolitical_risk":        geopolitical_risk,
        "hourly_demand":            hourly_demand,
        "units_per_staff_hour":     units_per_staff_hour,
        "min_staff_per_open_hour":  min_staff_per_open_hour,
        "max_staff":                max_staff,
        "hourly_wage":              hourly_wage,
        "open_hour":                open_hour,
        "close_hour":               close_hour,
        "depot_lat":                depot_lat,
        "depot_lon":                depot_lon,
        "stops":                    stops,
        "vehicle_capacity":         vehicle_capacity,
        "n_vehicles":               n_vehicles,
    })
    df.to_csv(OUT / "block_i.csv", index=False)
    print(f"block_i.csv — {len(df)} rows")


# ─────────────────────────────────────────────────────────────────────────────
# Block J — Fraud, AML & Identity (M-J1 .. M-J5)
# ─────────────────────────────────────────────────────────────────────────────
def gen_block_j():
    customer_ids   = [f"CUST-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]
    transaction_ids = [f"TXN-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]
    merchant_ids   = [f"MER-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]
    applicant_ids  = [f"APP-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]
    application_ids = [f"APPL-{str(uuid.uuid4())[:8].upper()}" for _ in range(N)]

    mccs = pick_mcc()

    # ── J1 features
    amount                 = RNG.uniform(5, 5_000, N).round(2)
    txn_count_last_24h     = RNG.integers(0, 25, N)
    txn_count_last_7d      = RNG.integers(0, 100, N)
    avg_amount_last_30d    = RNG.uniform(20, 500, N).round(2)
    distinct_merch_last_24h = RNG.integers(0, 15, N)
    is_foreign             = RNG.binomial(1, 0.10, N).astype(bool)
    is_cnp                 = RNG.binomial(1, 0.30, N).astype(bool)
    hour_of_day            = RNG.integers(0, 24, N)

    # ── J2 features (merchant)
    months_active          = RNG.integers(0, 120, N)
    chargeback_rate_30d    = RNG.beta(1.2, 30, N).round(4)
    refund_rate_30d        = RNG.beta(1.5, 25, N).round(4)
    avg_ticket_size        = RNG.uniform(5, 1500, N).round(2)
    txn_velocity_per_day   = RNG.gamma(2.0, 30.0, N).round(2)
    pct_cnp_transactions   = RNG.uniform(0, 1, N).round(3)
    pct_foreign_cards      = RNG.uniform(0, 0.6, N).round(3)
    prior_complaints_count = RNG.poisson(1.0, N)

    # ── J3 features (AML)
    cash_deposits_last_7d        = RNG.integers(0, 20, N)
    cash_amount_last_7d          = (cash_deposits_last_7d * RNG.uniform(500, 9_500, N)).round(2)
    structuring_threshold        = np.full(N, 10_000.0)
    near_threshold_deposits_30d  = RNG.integers(0, 12, N)
    rapid_in_out_count_30d       = RNG.integers(0, 25, N)
    distinct_counterparties_30d  = RNG.integers(0, 40, N)
    cross_border_count_30d       = RNG.integers(0, 15, N)
    high_risk_jurisdiction_count = RNG.integers(0, 5, N)

    # ── J4 features (synthetic identity)
    credit_file_age_months  = RNG.integers(0, 240, N)
    credit_inquiries_last_6m = RNG.integers(0, 12, N)
    address_changes_last_24m = RNG.integers(0, 6, N)
    ssn_age_norm            = RNG.uniform(0.3, 1.0, N).round(3)
    phone_tenure_months     = RNG.integers(0, 120, N)
    email_tenure_months     = RNG.integers(0, 120, N)
    distinct_names_at_address = RNG.integers(1, 7, N)
    employer_verifiable     = RNG.binomial(1, 0.85, N).astype(bool)

    # ── J5 features (application fraud)
    applications_last_24h    = RNG.integers(0, 6, N)
    applications_last_30d    = RNG.integers(0, 15, N)
    device_seen_count_30d    = RNG.integers(1, 8, N)
    ip_seen_count_30d        = RNG.integers(1, 8, N)
    declared_income          = RNG.uniform(500, 15_000, N).round(2)
    bureau_income_estimate   = (declared_income * RNG.uniform(0.4, 1.6, N)).round(2)
    document_quality_score   = RNG.beta(8, 2, N).round(3)
    velocity_score           = RNG.beta(1.2, 6, N).round(3)
    geolocation_mismatch     = RNG.binomial(1, 0.12, N).astype(bool)

    df = pd.DataFrame({
        "customer_id":                  customer_ids,
        "transaction_id":               transaction_ids,
        "merchant_id":                  merchant_ids,
        "applicant_id":                 applicant_ids,
        "application_id":               application_ids,
        "mcc_code":                     mccs,
        # J1
        "amount":                       amount,
        "txn_count_last_24h":           txn_count_last_24h,
        "txn_count_last_7d":            txn_count_last_7d,
        "avg_amount_last_30d":          avg_amount_last_30d,
        "distinct_merchants_last_24h":  distinct_merch_last_24h,
        "is_foreign":                   is_foreign,
        "is_cnp":                       is_cnp,
        "hour_of_day":                  hour_of_day,
        # J2
        "months_active":                months_active,
        "chargeback_rate_30d":          chargeback_rate_30d,
        "refund_rate_30d":              refund_rate_30d,
        "avg_ticket_size":              avg_ticket_size,
        "txn_velocity_per_day":         txn_velocity_per_day,
        "pct_cnp_transactions":         pct_cnp_transactions,
        "pct_foreign_cards":            pct_foreign_cards,
        "prior_complaints_count":       prior_complaints_count,
        # J3
        "cash_deposits_last_7d":        cash_deposits_last_7d,
        "cash_amount_last_7d":          cash_amount_last_7d,
        "structuring_threshold":        structuring_threshold,
        "near_threshold_deposits_30d":  near_threshold_deposits_30d,
        "rapid_in_out_count_30d":       rapid_in_out_count_30d,
        "distinct_counterparties_30d":  distinct_counterparties_30d,
        "cross_border_count_30d":       cross_border_count_30d,
        "high_risk_jurisdiction_count": high_risk_jurisdiction_count,
        # J4
        "credit_file_age_months":       credit_file_age_months,
        "credit_inquiries_last_6m":     credit_inquiries_last_6m,
        "address_changes_last_24m":     address_changes_last_24m,
        "ssn_age_norm":                 ssn_age_norm,
        "phone_tenure_months":          phone_tenure_months,
        "email_tenure_months":          email_tenure_months,
        "distinct_names_at_address":    distinct_names_at_address,
        "employer_verifiable":          employer_verifiable,
        # J5
        "applications_last_24h":        applications_last_24h,
        "applications_last_30d":        applications_last_30d,
        "device_seen_count_30d":        device_seen_count_30d,
        "ip_seen_count_30d":            ip_seen_count_30d,
        "declared_income":              declared_income,
        "bureau_income_estimate":       bureau_income_estimate,
        "document_quality_score":       document_quality_score,
        "velocity_score":               velocity_score,
        "geolocation_mismatch":         geolocation_mismatch,
    })
    df.to_csv(OUT / "block_j.csv", index=False)
    print(f"block_j.csv — {len(df)} rows")


# ─────────────────────────────────────────────────────────────────────────────
# Run all generators
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Generating {N} rows per block → {OUT}/\n")
    gen_block_a()
    gen_block_b()
    gen_block_c()
    gen_block_d()
    gen_block_e()
    gen_block_f()
    gen_block_g()
    gen_block_h()
    gen_block_i()
    gen_block_j()
    print(f"\nDone. 10 files written to {OUT}/")
