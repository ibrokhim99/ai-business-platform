#!/usr/bin/env python3
"""
Evaluate every registered ML model against its block-level test CSV.

For each model we:
  1. Build the input schema instance from each row in data/test/block_<X>.csv
  2. Call model.predict() (and optionally explain()) with timing
  3. Capture success/error and per-model output statistics
  4. Write a JSON detail report and a Markdown summary

Usage (from repo root, inside the backend container or a venv with the deps):
    python backend/scripts/evaluate_models.py
    python backend/scripts/evaluate_models.py --rows 100
    python backend/scripts/evaluate_models.py --models M-A1 M-J1 --explain
    python backend/scripts/evaluate_models.py --report-dir reports/
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from pydantic import BaseModel, ValidationError

# ─── Make `app.*` importable when run from anywhere ──────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ml.registry import get_registry  # noqa: E402
from app.schemas import (  # noqa: E402
    block_a, block_b, block_c, block_d, block_e,
    block_f, block_g, block_h, block_i, block_j,
)

DEFAULT_DATA_DIR = REPO_ROOT / "data" / "test"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports"


# ── Block lookup ─────────────────────────────────────────────────────────────
def _block_letter(model_id: str) -> str:
    """'M-A1' -> 'a'."""
    return model_id.split("-")[1][0].lower()


# ── Light value coercion helpers ─────────────────────────────────────────────
def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def _parse_json_list(s: Any, default: list | None = None) -> list:
    if default is None:
        default = []
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return default
    if isinstance(s, list):
        return s
    s = str(s).strip()
    if not s:
        return default
    try:
        v = json.loads(s)
        return v if isinstance(v, list) else default
    except json.JSONDecodeError:
        return [p.strip() for p in s.split(",") if p.strip()]


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    return s in {"1", "true", "t", "yes", "y"}


# ─── Per-model input builders ────────────────────────────────────────────────
# Each entry: model_id -> (InputSchemaClass, build_kwargs(row, df_block) -> dict)
# `df_block` is passed for builders that need a candidate pool (e.g. M-H6).

InputBuilder = Callable[[dict, pd.DataFrame], dict]


def _b(cls: type[BaseModel], builder: InputBuilder) -> tuple[type[BaseModel], InputBuilder]:
    return cls, builder


# ── Block A ──────────────────────────────────────────────────────────────────
def _a1(row, _df):
    return dict(
        region_id=row["region_id"], mcc_code=str(row["mcc_code"]),
        population=int(row["population"]), avg_income=float(row["avg_income"]),
        niche=row.get("niche", ""),
    )


def _a2(row, _df):
    return dict(
        region_id=row["region_id"], mcc_code=str(row["mcc_code"]),
        normative_density=float(row["normative_density"]),
        actual_count=int(row["actual_count"]),
        population=int(row["population"]),
    )


def _a3(row, _df):
    return dict(
        region_id=row["region_id"], mcc_code=str(row["mcc_code"]),
        competitor_count=int(row["competitor_count"]),
        population=int(row["population"]),
        avg_revenue_per_outlet=float(row["avg_revenue_per_outlet"]),
    )


def _a4(row, _df):
    return dict(
        region_id=row["region_id"], mcc_code=str(row["mcc_code"]),
        population=int(row["population"]),
        avg_monthly_spend=float(row["avg_monthly_spend"]),
        competitor_count=int(row["competitor_count"]),
    )


def _a5(row, _df):
    return dict(
        region_id=row["region_id"], mcc_code=str(row["mcc_code"]),
        population=int(row["population"]), avg_income=float(row["avg_income"]),
        competitor_count=int(row["competitor_count"]),
        growth_rate_pct=float(row.get("growth_rate_pct", 0.0)),
    )


def _a6(row, _df):
    return dict(
        new_mcc_code=str(row["mcc_code"]),
        location_lat=float(row["location_lat"]),
        location_lon=float(row["location_lon"]),
        radius_m=int(_clip(int(row["radius_m"]), 100, 2000)),
        adjacent_mcc_codes=_parse_json_list(row.get("adjacent_mcc_codes")),
    )


# ── Block B ──────────────────────────────────────────────────────────────────
def _b1(row, _df):
    return dict(
        region_id=row["region_id"], mcc_code=str(row["mcc_code"]),
        horizon_months=int(_clip(int(row["horizon_months"]), 1, 36)),
        base_monthly_revenue=float(row["base_monthly_revenue"]),
    )


def _b2(row, _df):
    return dict(
        mcc_code=str(row["mcc_code"]), region_id=row["region_id"],
        year=int(_clip(int(row["year"]), 2020, 2030)),
    )


def _b3(row, _df):
    return dict(
        region_id=row["region_id"],
        horizon_years=int(_clip(int(row["horizon_years"]), 1, 20)),
    )


def _b4(row, _df):
    return dict(
        region_id=row["region_id"],
        horizon_months=int(_clip(int(row["horizon_months"]), 3, 36)),
        current_avg_income=float(row["current_avg_income"]),
    )


def _b5(row, _df):
    return dict(
        mcc_code=str(row["mcc_code"]), region_id=row["region_id"],
        lookback_months=int(_clip(int(row["lookback_months"]), 6, 60)),
    )


def _b6(row, _df):
    return dict(
        region_id=row["region_id"], mcc_code=str(row["mcc_code"]),
        horizon_months=int(_clip(int(row["horizon_months"]), 3, 24)),
    )


# ── Block C ──────────────────────────────────────────────────────────────────
def _c1(row, _df):
    return dict(
        lat=float(row["lat"]), lon=float(row["lon"]),
        mcc_code=str(row["mcc_code"]),
        radius_m=int(_clip(int(row["radius_m"]), 100, 2000)),
    )


def _c2(row, _df):
    return dict(
        lat=float(row["lat"]), lon=float(row["lon"]),
        radius_m=int(_clip(int(row["radius_m"]), 50, 1000)),
    )


def _c3(row, _df):
    walk = _parse_json_list(row.get("walk_minutes"), [5, 10])
    walk = [int(w) for w in walk] or [10]
    return dict(
        lat=float(row["lat"]), lon=float(row["lon"]),
        walk_minutes=walk, mcc_code=str(row["mcc_code"]),
    )


def _c4(row, _df):
    return dict(
        lat=float(row["lat"]), lon=float(row["lon"]),
        radius_m=int(_clip(int(row["radius_m"]), 50, 1000)),
    )


def _c5(row, _df):
    return dict(
        lat=float(row["lat"]), lon=float(row["lon"]),
        radius_m=int(_clip(int(row["radius_m"]), 100, 2000)),
    )


def _c6(row, _df):
    return dict(
        lat=float(row["lat"]), lon=float(row["lon"]),
        facade_direction_deg=float(_clip(float(row["facade_direction_deg"]), 0, 360)),
    )


# ── Block D ──────────────────────────────────────────────────────────────────
def _d1(row, _df):
    return dict(
        mcc_code=str(row["mcc_code"]), region_id=row["region_id"],
        monthly_revenue_estimate=float(row["monthly_revenue_estimate"]),
        monthly_fixed_costs=float(row["monthly_fixed_costs"]),
        initial_investment=float(row["initial_investment"]),
        monthly_rent=float(row["monthly_rent"]),
    )


def _d2(row, _df):
    return dict(
        mcc_code=str(row["mcc_code"]),
        avg_transaction_value=float(row["avg_transaction_value"]),
        monthly_transactions=int(row["monthly_transactions"]),
        customer_acquisition_cost=float(row["customer_acquisition_cost"]),
        monthly_churn_rate_pct=float(row["monthly_churn_rate_pct"]),
        gross_margin_pct=float(row["gross_margin_pct"]),
    )


def _d3(row, _df):
    return dict(
        initial_investment=float(row["initial_investment"]),
        monthly_net_cash_flow=float(row["monthly_net_cash_flow"]),
        discount_rate_annual_pct=float(row["discount_rate_annual_pct"]),
        horizon_years=int(_clip(int(row["horizon_years"]), 1, 10)),
    )


def _d4(row, _df):
    return dict(
        mcc_code=str(row["mcc_code"]),
        monthly_revenue_estimate=float(row["monthly_revenue_estimate"]),
        monthly_rent=float(row["monthly_rent"]),
    )


def _d5(row, _df):
    return dict(
        mcc_code=str(row["mcc_code"]), region_id=row["region_id"],
        initial_investment=float(row["initial_investment"]),
        monthly_revenue_base=float(row["monthly_revenue_estimate"]),
        monthly_fixed_costs=float(row["monthly_fixed_costs"]),
        cogs_pct=float(row["cogs_pct"]),
        growth_rate_monthly_pct=float(row["growth_rate_monthly_pct"]),
        horizon_months=int(_clip(int(row["horizon_months"]), 6, 36)),
    )


def _d6(row, _df):
    return dict(
        mcc_code=str(row["mcc_code"]),
        monthly_revenue=float(row["monthly_revenue"]),
        region_id=row.get("region_id", ""),
    )


# ── Block E ──────────────────────────────────────────────────────────────────
def _e1(row, _df):
    return dict(
        lat=float(row["lat"]), lon=float(row["lon"]),
        mcc_code=str(row["mcc_code"]),
        radius_300m=_to_bool(row.get("radius_300m", True)),
        radius_1km=_to_bool(row.get("radius_1km", True)),
    )


def _e2(row, _df):
    return dict(
        mcc_code=str(row["mcc_code"]), region_id=row["region_id"],
        monthly_revenue=float(row["monthly_revenue"]),
        initial_investment=float(row["initial_investment"]),
        owner_experience_years=float(row["owner_experience_years"]),
        location_score=float(_clip(float(row["location_score"]), 0, 100)),
        competition_count=int(row["competition_count"]),
    )


def _e3(row, _df):
    return dict(
        mcc_code=str(row["mcc_code"]), region_id=row["region_id"],
        business_age_months=int(row["business_age_months"]),
    )


def _e4(row, _df):
    return dict(
        mcc_code=str(row["mcc_code"]), region_id=row["region_id"],
        initial_investment=float(row["initial_investment"]),
    )


def _e5(row, _df):
    return dict(
        mcc_code=str(row["mcc_code"]), region_id=row["region_id"],
        target_price=float(row["target_price"]),
        competitor_avg_price=float(row["competitor_avg_price"]),
    )


# ── Block F ──────────────────────────────────────────────────────────────────
def _f1(row, _df):
    return dict(
        customer_id=row["customer_id"], mcc_code=str(row["mcc_code"]),
        region_id=row["region_id"],
        lat=float(row["lat"]), lon=float(row["lon"]),
        monthly_revenue_estimate=float(row["monthly_revenue_estimate"]),
        requested_loan_amount=float(row["requested_loan_amount"]),
        business_age_months=int(row["business_age_months"]),
        owner_credit_history_score=float(_clip(float(row["owner_credit_history_score"]), 300, 850)),
        collateral_value=float(row["collateral_value"]),
    )


def _f2(row, _df):
    return dict(
        monthly_net_cashflow=float(row["monthly_net_cashflow"]),
        monthly_revenue=float(row["monthly_revenue"]),
        existing_debt_monthly=float(row["existing_debt_monthly"]),
        loan_term_months=int(_clip(int(row["loan_term_months"]), 6, 120)),
        interest_rate_annual_pct=float(_clip(float(row["interest_rate_annual_pct"]), 0, 100)),
    )


def _f3(row, _df):
    return dict(
        mcc_code=str(row["mcc_code"]), region_id=row["region_id"],
        initial_monthly_revenue=float(row["initial_monthly_revenue"]),
        proposed_loan_amount=float(row["proposed_loan_amount"]),
        loan_term_months=int(_clip(int(row["loan_term_months"]), 6, 120)),
        interest_rate_annual_pct=float(row["interest_rate_annual_pct"]),
    )


def _f4(row, _df):
    return dict(
        customer_id=row["customer_id"], loan_id=row["loan_id"],
        months_since_disbursement=int(row["months_since_disbursement"]),
        payment_delays_count=int(row["payment_delays_count"]),
        revenue_trend_3m_pct=float(row["revenue_trend_3m_pct"]),
        current_dti=float(row["current_dti"]),
        location_score=50.0,  # not in CSV
    )


def _f5(row, _df):
    return dict(
        customer_id=row["customer_id"], mcc_code=str(row["mcc_code"]),
        monthly_revenue=float(row["monthly_revenue"]),
        business_age_months=int(row["business_age_months"]),
        existing_products=_parse_json_list(row.get("existing_products")),
        credit_score=float(_clip(float(row["credit_score"]), 300, 1000)),
    )


# ── Block G ──────────────────────────────────────────────────────────────────
def _g1(row, _df):
    return dict(
        lat=float(row["lat"]), lon=float(row["lon"]),
        radius_m=int(_clip(int(row["radius_m"]), 100, 2000)),
        mcc_code=str(row["mcc_code"]),
    )


def _g2(row, _df):
    return dict(
        lat=float(row["lat"]), lon=float(row["lon"]),
        radius_m=int(_clip(int(row["radius_m"]), 100, 2000)),
        hour_of_day=int(_clip(int(row["hour_of_day"]), 0, 23)),
        day_of_week=int(_clip(int(row["day_of_week"]), 0, 6)),
    )


def _g3(row, _df):
    return dict(
        lat=float(row["lat"]), lon=float(row["lon"]),
        radius_m=int(_clip(int(row["radius_m"]), 100, 2000)),
        mcc_code=str(row["mcc_code"]),
    )


def _g4(row, _df):
    return dict(
        lat=float(row["lat"]), lon=float(row["lon"]),
        radius_m=int(_clip(int(row["radius_m"]), 100, 2000)),
        mcc_code=str(row["mcc_code"]),
    )


def _g5(row, _df):
    return dict(
        lat=float(row["lat"]), lon=float(row["lon"]),
        radius_m=int(_clip(int(row["radius_m"]), 200, 5000)),
    )


# ── Block H ──────────────────────────────────────────────────────────────────
def _h1(row, _df):
    return dict(
        channel=row["channel"], region_id=row["region_id"],
        monthly_budget=float(row["monthly_budget"]),
        industry_mcc=str(row["industry_mcc"]),
        target_segment=row["target_segment"],
        historical_cac=float(row["historical_cac"]),
        competition_intensity=float(_clip(float(row["competition_intensity"]), 0, 1)),
    )


def _h2(row, _df):
    return dict(
        arpu_monthly=float(row["arpu_monthly"]),
        gross_margin_pct=float(_clip(float(row["gross_margin_pct"]), 0, 1)),
        monthly_churn_rate=float(_clip(float(row["monthly_churn_rate"]), 1e-4, 1.0)),
        discount_rate_annual=float(_clip(float(row["discount_rate_annual"]), 0, 1)),
        cac=float(row["cac"]),
    )


def _h3(row, _df):
    tps = _parse_json_list(row.get("touchpoints"))
    if not tps:
        tps = ["organic"]
    return dict(
        journey_id=row["journey_id"],
        touchpoints=[str(x) for x in tps],
        conversion_value=float(row["conversion_value"]),
    )


def _h4(row, _df):
    return dict(
        customer_id=row["customer_id"],
        promo_type=row["promo_type"],
        promo_value=float(row["promo_value"]),
        customer_recency_days=int(row["customer_recency_days"]),
        customer_frequency_30d=int(row["customer_frequency_30d"]),
        customer_monetary_30d=float(row["customer_monetary_30d"]),
        historical_response_rate=float(_clip(float(row["historical_response_rate"]), 0, 1)),
    )


def _h5(row, _df):
    elasticity = float(row["elasticity_estimate"])
    if elasticity >= 0:
        elasticity = -1.5
    return dict(
        product_id=row["product_id"],
        current_price=float(row["current_price"]),
        current_units_sold=float(row["current_units_sold"]),
        unit_cost=float(row["unit_cost"]),
        elasticity_estimate=elasticity,
    )


_H6_FEATURE_COLS = (
    "monthly_budget", "historical_cac", "competition_intensity",
    "arpu_monthly", "gross_margin_pct", "monthly_churn_rate", "cac",
    "promo_value", "customer_recency_days", "customer_frequency_30d",
    "customer_monetary_30d", "current_price", "current_units_sold", "unit_cost",
)


def _h6_features(row: dict) -> dict:
    feats: dict[str, float] = {}
    for c in _H6_FEATURE_COLS:
        v = row.get(c)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            continue
        try:
            feats[c] = float(v)
        except (TypeError, ValueError):
            continue
    return feats


def _h6(row, df):
    pool_n = min(50, len(df))
    pool_df = df.sample(n=pool_n, random_state=int(abs(hash(row.get("customer_id", ""))) % 2**32))
    candidate_pool = []
    for _, r in pool_df.iterrows():
        feats = _h6_features(r.to_dict())
        feats["customer_id"] = r["customer_id"]
        candidate_pool.append(feats)
    return dict(
        seed_customer_features=_h6_features(row),
        candidate_pool=candidate_pool,
        top_k=10,
    )


# ── Block I ──────────────────────────────────────────────────────────────────
def _i1(row, _df):
    return dict(
        sku_id=row["sku_id"],
        annual_demand=float(row["annual_demand"]),
        unit_cost=float(row["unit_cost"]),
        ordering_cost=float(row["ordering_cost"]),
        holding_cost_pct=float(_clip(float(row["holding_cost_pct"]), 1e-3, 1.0)),
        lead_time_days=float(row["lead_time_days"]),
        demand_std_daily=float(row["demand_std_daily"]),
        service_level=float(_clip(float(row["service_level"]), 0.5, 0.999)),
    )


def _i2(row, _df):
    return dict(
        sku_id=row["sku_id"],
        on_hand_units=float(row["on_hand_units"]),
        on_order_units=float(row["on_order_units"]),
        daily_demand_mean=float(max(0.01, float(row["daily_demand_mean"]))),
        daily_demand_std=float(row["daily_demand_std"]),
        lead_time_days_mean=float(max(0.1, float(row["lead_time_days_mean"]))),
        lead_time_days_std=float(row["lead_time_days_std"]),
        horizon_days=int(row["horizon_days"]),
    )


def _i3(row, _df):
    return dict(
        supplier_id=row["supplier_id"],
        months_active=int(row["months_active"]),
        on_time_delivery_rate=float(_clip(float(row["on_time_delivery_rate"]), 0, 1)),
        quality_defect_rate=float(_clip(float(row["quality_defect_rate"]), 0, 1)),
        payment_terms_days=int(row["payment_terms_days"]),
        payment_delay_avg_days=float(row["payment_delay_avg_days"]),
        revenue_concentration_pct=float(_clip(float(row["revenue_concentration_pct"]), 0, 1)),
        single_source_flag=_to_bool(row["single_source_flag"]),
        geopolitical_risk=float(_clip(float(row["geopolitical_risk"]), 0, 1)),
    )


def _i4(row, _df):
    hd = _parse_json_list(row.get("hourly_demand"))
    hd = [float(x) for x in hd]
    if len(hd) < 24:
        hd = (hd + [0.0] * 24)[:24]
    elif len(hd) > 24:
        hd = hd[:24]
    open_h = int(_clip(int(row["open_hour"]), 0, 23))
    close_h = int(_clip(int(row["close_hour"]), 0, 23))
    return dict(
        location_id=row["location_id"],
        hourly_demand=hd,
        units_per_staff_hour=float(row["units_per_staff_hour"]),
        min_staff_per_open_hour=int(row["min_staff_per_open_hour"]),
        max_staff=int(row["max_staff"]),
        hourly_wage=float(row["hourly_wage"]),
        open_hour=open_h,
        close_hour=close_h,
    )


def _i5(row, _df):
    stops_raw = _parse_json_list(row.get("stops"))
    stops = []
    for s in stops_raw:
        if isinstance(s, dict) and "lat" in s and "lon" in s:
            stops.append({
                "stop_id": str(s.get("stop_id", f"S{len(stops)+1}")),
                "lat": float(s["lat"]),
                "lon": float(s["lon"]),
                "demand": float(s.get("demand", 1.0)),
            })
    if not stops:
        stops = [{"stop_id": "S1", "lat": float(row["depot_lat"]),
                  "lon": float(row["depot_lon"]), "demand": 1.0}]
    return dict(
        depot_lat=float(row["depot_lat"]),
        depot_lon=float(row["depot_lon"]),
        stops=stops,
        vehicle_capacity=float(row["vehicle_capacity"]),
        n_vehicles=int(_clip(int(row["n_vehicles"]), 1, 20)),
    )


# ── Block J ──────────────────────────────────────────────────────────────────
def _j1(row, _df):
    return dict(
        customer_id=row["customer_id"], transaction_id=row["transaction_id"],
        amount=float(row["amount"]), mcc_code=str(row["mcc_code"]),
        txn_count_last_24h=int(row["txn_count_last_24h"]),
        txn_count_last_7d=int(row["txn_count_last_7d"]),
        avg_amount_last_30d=float(row["avg_amount_last_30d"]),
        distinct_merchants_last_24h=int(row["distinct_merchants_last_24h"]),
        is_foreign=_to_bool(row["is_foreign"]),
        is_cnp=_to_bool(row["is_cnp"]),
        hour_of_day=int(_clip(int(row["hour_of_day"]), 0, 23)),
    )


def _j2(row, _df):
    return dict(
        merchant_id=row["merchant_id"], mcc_code=str(row["mcc_code"]),
        months_active=int(row["months_active"]),
        chargeback_rate_30d=float(_clip(float(row["chargeback_rate_30d"]), 0, 1)),
        refund_rate_30d=float(_clip(float(row["refund_rate_30d"]), 0, 1)),
        avg_ticket_size=float(row["avg_ticket_size"]),
        txn_velocity_per_day=float(row["txn_velocity_per_day"]),
        pct_cnp_transactions=float(_clip(float(row["pct_cnp_transactions"]), 0, 1)),
        pct_foreign_cards=float(_clip(float(row["pct_foreign_cards"]), 0, 1)),
        prior_complaints_count=int(row["prior_complaints_count"]),
    )


def _j3(row, _df):
    return dict(
        customer_id=row["customer_id"],
        cash_deposits_last_7d=int(row["cash_deposits_last_7d"]),
        cash_amount_last_7d=float(row["cash_amount_last_7d"]),
        structuring_threshold=float(row["structuring_threshold"]),
        near_threshold_deposits_30d=int(row["near_threshold_deposits_30d"]),
        rapid_in_out_count_30d=int(row["rapid_in_out_count_30d"]),
        distinct_counterparties_30d=int(row["distinct_counterparties_30d"]),
        cross_border_count_30d=int(row["cross_border_count_30d"]),
        high_risk_jurisdiction_count=int(row["high_risk_jurisdiction_count"]),
    )


def _j4(row, _df):
    return dict(
        applicant_id=row["applicant_id"],
        credit_file_age_months=int(row["credit_file_age_months"]),
        credit_inquiries_last_6m=int(row["credit_inquiries_last_6m"]),
        address_changes_last_24m=int(row["address_changes_last_24m"]),
        ssn_age_norm=float(_clip(float(row["ssn_age_norm"]), 0, 1)),
        phone_tenure_months=int(row["phone_tenure_months"]),
        email_tenure_months=int(row["email_tenure_months"]),
        distinct_names_at_address=int(max(1, int(row["distinct_names_at_address"]))),
        employer_verifiable=_to_bool(row["employer_verifiable"]),
    )


def _j5(row, _df):
    return dict(
        application_id=row["application_id"],
        applications_last_24h=int(row["applications_last_24h"]),
        applications_last_30d=int(row["applications_last_30d"]),
        device_seen_count_30d=int(max(1, int(row["device_seen_count_30d"]))),
        ip_seen_count_30d=int(max(1, int(row["ip_seen_count_30d"]))),
        declared_income=float(row["declared_income"]),
        bureau_income_estimate=float(row["bureau_income_estimate"]),
        document_quality_score=float(_clip(float(row["document_quality_score"]), 0, 1)),
        velocity_score=float(_clip(float(row["velocity_score"]), 0, 1)),
        geolocation_mismatch=_to_bool(row["geolocation_mismatch"]),
    )


# ─── Registry of input builders ──────────────────────────────────────────────
INPUT_BUILDERS: dict[str, tuple[type[BaseModel], InputBuilder]] = {
    "M-A1": _b(block_a.MarketSizingIn,       _a1),
    "M-A2": _b(block_a.GapAnalysisIn,        _a2),
    "M-A3": _b(block_a.SaturationIndexIn,    _a3),
    "M-A4": _b(block_a.WalletShareIn,        _a4),
    "M-A5": _b(block_a.NicheOpportunityIn,   _a5),
    "M-A6": _b(block_a.CrossNicheIn,         _a6),

    "M-B1": _b(block_b.DemandForecastIn,         _b1),
    "M-B2": _b(block_b.SeasonalityIn,            _b2),
    "M-B3": _b(block_b.PopulationDynamicsIn,     _b3),
    "M-B4": _b(block_b.IncomeTrendIn,            _b4),
    "M-B5": _b(block_b.MCCTrendIn,               _b5),
    "M-B6": _b(block_b.BusinessRegistrationIn,   _b6),

    "M-C1": _b(block_c.LocationScoreIn,    _c1),
    "M-C2": _b(block_c.TrafficScoringIn,   _c2),
    "M-C3": _b(block_c.IsochroneDemandIn,  _c3),
    "M-C4": _b(block_c.StreetVitalityIn,   _c4),
    "M-C5": _b(block_c.AnchorEffectIn,     _c5),
    "M-C6": _b(block_c.VisibilityScoreIn,  _c6),

    "M-D1": _b(block_d.ViabilityCheckIn,    _d1),
    "M-D2": _b(block_d.UnitEconomicsIn,     _d2),
    "M-D3": _b(block_d.ROIEstimatorIn,      _d3),
    "M-D4": _b(block_d.RentalBurdenIn,      _d4),
    "M-D5": _b(block_d.CashFlowSimIn,       _d5),
    "M-D6": _b(block_d.COGSMarginIn,        _d6),

    "M-E1": _b(block_e.CompetitorIntelIn,   _e1),
    "M-E2": _b(block_e.ChurnPredictionIn,   _e2),
    "M-E3": _b(block_e.RegulatoryRiskIn,    _e3),
    "M-E4": _b(block_e.EntryBarrierIn,      _e4),
    "M-E5": _b(block_e.PricePressureIn,     _e5),

    "M-F1": _b(block_f.CreditRiskIn,            _f1),
    "M-F2": _b(block_f.LoanSizingIn,            _f2),
    "M-F3": _b(block_f.DTIPredictorIn,          _f3),
    "M-F4": _b(block_f.NPLWarningIn,            _f4),
    "M-F5": _b(block_f.ProductRecommenderIn,    _f5),

    "M-G1": _b(block_g.CustomerProfilerIn,    _g1),
    "M-G2": _b(block_g.DayPopulationIn,       _g2),
    "M-G3": _b(block_g.BehaviorClassifierIn,  _g3),
    "M-G4": _b(block_g.BrandAffinityIn,       _g4),
    "M-G5": _b(block_g.SpendingPowerIn,       _g5),

    "M-H1": _b(block_h.CACPredictorIn,         _h1),
    "M-H2": _b(block_h.LTVCACRatioIn,          _h2),
    "M-H3": _b(block_h.ChannelAttributionIn,   _h3),
    "M-H4": _b(block_h.PromoUpliftIn,          _h4),
    "M-H5": _b(block_h.OptimalPricingIn,       _h5),
    "M-H6": _b(block_h.LookalikeAudienceIn,    _h6),

    "M-I1": _b(block_i.InventoryOptimizerIn,   _i1),
    "M-I2": _b(block_i.StockoutRiskIn,         _i2),
    "M-I3": _b(block_i.SupplierRiskIn,         _i3),
    "M-I4": _b(block_i.StaffingOptimizerIn,    _i4),
    "M-I5": _b(block_i.DeliveryRoutingIn,      _i5),

    "M-J1": _b(block_j.TransactionAnomalyIn,  _j1),
    "M-J2": _b(block_j.MerchantFraudIn,       _j2),
    "M-J3": _b(block_j.AMLPatternIn,          _j3),
    "M-J4": _b(block_j.SyntheticIdentityIn,   _j4),
    "M-J5": _b(block_j.ApplicationFraudIn,    _j5),
}


# ─── Output summarisation ────────────────────────────────────────────────────
SCALAR_TYPES = (int, float, bool, str)


def _summarise_scalar(values: list) -> dict:
    if not values:
        return {}
    if all(isinstance(v, bool) for v in values):
        c = Counter(values)
        return {"true": c.get(True, 0), "false": c.get(False, 0)}
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        nums = [float(v) for v in values]
        return {
            "min": round(min(nums), 4),
            "max": round(max(nums), 4),
            "mean": round(statistics.fmean(nums), 4),
            "median": round(statistics.median(nums), 4),
        }
    if all(isinstance(v, str) for v in values):
        c = Counter(values)
        return {"top": c.most_common(5)}
    return {}


def _summarise_outputs(outputs: list[dict]) -> dict:
    """For each output field that is a scalar, compute a summary."""
    if not outputs:
        return {}
    summary: dict[str, dict] = {}
    keys = set().union(*(o.keys() for o in outputs))
    for k in sorted(keys):
        vals = [o[k] for o in outputs if k in o and o[k] is not None]
        if not vals:
            continue
        if all(isinstance(v, SCALAR_TYPES) for v in vals):
            s = _summarise_scalar(vals)
            if s:
                summary[k] = s
    return summary


# ─── Evaluation core ─────────────────────────────────────────────────────────
def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * pct / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def evaluate_one(
    model_id: str, registry, df: pd.DataFrame, *, max_rows: int, include_explanation: bool,
) -> dict:
    if model_id not in INPUT_BUILDERS:
        return {"model_id": model_id, "error": "no input builder configured"}

    cls, builder = INPUT_BUILDERS[model_id]
    rows = df.head(max_rows).to_dict("records") if max_rows > 0 else df.to_dict("records")

    model = registry.get(model_id)
    meta = model.get_metadata().model_dump()

    pred_latencies: list[float] = []
    expl_latencies: list[float] = []
    successes = 0
    validation_errors: list[str] = []
    runtime_errors: list[str] = []
    validation_count = 0
    runtime_count = 0
    outputs_collected: list[dict] = []
    sample_input: dict | None = None
    sample_output: dict | None = None
    sample_error: str | None = None

    for row in rows:
        try:
            kwargs = builder(row, df)
            payload = cls(**kwargs)
        except (ValidationError, ValueError, TypeError, KeyError) as e:
            validation_count += 1
            if len(validation_errors) < 3:
                validation_errors.append(f"{type(e).__name__}: {e}")
            continue

        try:
            t0 = time.perf_counter()
            out = model.predict(payload)
            pred_latencies.append((time.perf_counter() - t0) * 1000)
            successes += 1

            out_dict = out.model_dump() if hasattr(out, "model_dump") else dict(out)
            outputs_collected.append(out_dict)
            if sample_output is None:
                sample_input = payload.model_dump()
                sample_output = out_dict

            if include_explanation:
                t0 = time.perf_counter()
                _ = model.explain(payload)
                expl_latencies.append((time.perf_counter() - t0) * 1000)
        except Exception as e:
            runtime_count += 1
            if len(runtime_errors) < 3:
                runtime_errors.append(f"{type(e).__name__}: {e}")
            if sample_error is None:
                sample_error = traceback.format_exc(limit=2)

    n = len(rows)
    return {
        "model_id": model_id,
        "block": meta.get("block"),
        "name": meta.get("name"),
        "version": meta.get("version"),
        "is_stub": meta.get("is_stub"),
        "n_rows": n,
        "n_success": successes,
        "n_validation_errors": validation_count,
        "n_runtime_errors": runtime_count,
        "success_rate": round(successes / n, 4) if n else 0.0,
        "latency_ms": {
            "p50": round(_percentile(pred_latencies, 50), 3),
            "p95": round(_percentile(pred_latencies, 95), 3),
            "mean": round(statistics.fmean(pred_latencies), 3) if pred_latencies else 0.0,
            "min": round(min(pred_latencies), 3) if pred_latencies else 0.0,
            "max": round(max(pred_latencies), 3) if pred_latencies else 0.0,
        },
        "explain_latency_ms": (
            {
                "p50": round(_percentile(expl_latencies, 50), 3),
                "p95": round(_percentile(expl_latencies, 95), 3),
                "mean": round(statistics.fmean(expl_latencies), 3),
            }
            if expl_latencies
            else None
        ),
        "validation_error_samples": validation_errors,
        "runtime_error_samples": runtime_errors,
        "runtime_error_traceback": sample_error,
        "output_summary": _summarise_outputs(outputs_collected),
        "sample_input": sample_input,
        "sample_output": sample_output,
    }


def evaluate(
    *,
    data_dir: Path,
    model_filter: list[str] | None,
    max_rows: int,
    include_explanation: bool,
) -> dict:
    registry = get_registry()
    all_ids = registry.all_ids()
    target_ids = [m for m in all_ids if (not model_filter or m in model_filter)]
    if model_filter:
        missing = [m for m in model_filter if m not in all_ids]
        if missing:
            print(f"WARN: unknown model ids skipped: {missing}", file=sys.stderr)

    # Cache one CSV per block
    block_cache: dict[str, pd.DataFrame] = {}

    results: list[dict] = []
    for mid in target_ids:
        block = _block_letter(mid)
        if block not in block_cache:
            csv_path = data_dir / f"block_{block}.csv"
            if not csv_path.exists():
                print(f"SKIP {mid}: missing CSV {csv_path}", file=sys.stderr)
                continue
            block_cache[block] = pd.read_csv(csv_path)
        df = block_cache[block]

        print(f"  → {mid:6s} ({len(df)} rows available, evaluating up to {max_rows})", flush=True)
        res = evaluate_one(
            mid, registry, df,
            max_rows=max_rows,
            include_explanation=include_explanation,
        )
        results.append(res)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_models_evaluated": len(results),
        "max_rows_per_model": max_rows,
        "include_explanation": include_explanation,
        "results": results,
    }


# ─── Markdown report ─────────────────────────────────────────────────────────
def render_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Model Evaluation Report")
    lines.append("")
    lines.append(f"- Generated: `{report['generated_at']}`")
    lines.append(f"- Models evaluated: **{report['n_models_evaluated']}**")
    lines.append(f"- Rows per model: **{report['max_rows_per_model']}**")
    lines.append(f"- Explainer included: **{report['include_explanation']}**")
    lines.append("")

    # Aggregate stats
    res = report["results"]
    n_total = sum(r.get("n_rows", 0) for r in res)
    n_ok = sum(r.get("n_success", 0) for r in res)
    n_val = sum(r.get("n_validation_errors", 0) for r in res)
    n_run = sum(r.get("n_runtime_errors", 0) for r in res)
    overall = n_ok / n_total if n_total else 0.0
    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- Total predictions attempted: **{n_total}**")
    lines.append(f"- Successful: **{n_ok}** ({overall:.1%})")
    lines.append(f"- Validation errors: **{n_val}**")
    lines.append(f"- Runtime errors: **{n_run}**")
    lines.append("")

    # Per-model table
    lines.append("## Per-model summary")
    lines.append("")
    lines.append("| Model | Block | Stub | Rows | Success | Val. err | Run. err | p50 (ms) | p95 (ms) | Mean (ms) |")
    lines.append("|-------|-------|------|-----:|--------:|---------:|---------:|---------:|---------:|----------:|")
    for r in res:
        if "error" in r:
            lines.append(f"| {r['model_id']} | – | – | – | – | – | – | – | – | – |")
            continue
        lat = r.get("latency_ms") or {}
        sr = r.get("success_rate", 0.0)
        lines.append(
            f"| {r['model_id']} | {r.get('block', '?')} | "
            f"{'Y' if r.get('is_stub') else 'N'} | {r.get('n_rows', 0)} | "
            f"{r.get('n_success', 0)} ({sr:.0%}) | "
            f"{r.get('n_validation_errors', 0)} | {r.get('n_runtime_errors', 0)} | "
            f"{lat.get('p50', 0)} | {lat.get('p95', 0)} | {lat.get('mean', 0)} |"
        )
    lines.append("")

    # Errors section
    failing = [r for r in res if r.get("n_runtime_errors", 0) or r.get("n_validation_errors", 0)]
    if failing:
        lines.append("## Errors")
        lines.append("")
        for r in failing:
            lines.append(f"### {r['model_id']} — {r.get('name', '')}")
            if r.get("validation_error_samples"):
                lines.append("**Validation:**")
                for e in r["validation_error_samples"]:
                    lines.append(f"- `{e[:240]}`")
            if r.get("runtime_error_samples"):
                lines.append("**Runtime:**")
                for e in r["runtime_error_samples"]:
                    lines.append(f"- `{e[:240]}`")
            lines.append("")

    return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────────────────
def main() -> int:
    p = argparse.ArgumentParser(description="Evaluate every registered ML model on the test CSVs.")
    p.add_argument("--models", nargs="*", default=None,
                   help="Optional whitelist of model IDs (e.g. M-A1 M-J3). Default: all.")
    p.add_argument("--rows", type=int, default=100,
                   help="Max rows per model to evaluate. Use 0 for the full file. Default: 100.")
    p.add_argument("--explain", action="store_true",
                   help="Also call .explain() and time it (slower, especially for SHAP-backed models).")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                   help=f"Directory with block_<X>.csv test files. Default: {DEFAULT_DATA_DIR}")
    p.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR,
                   help=f"Output directory. Default: {DEFAULT_REPORT_DIR}")
    p.add_argument("--no-markdown", action="store_true",
                   help="Skip the Markdown report (only write JSON).")
    args = p.parse_args()

    if not args.data_dir.exists():
        print(f"ERROR: test data not found at {args.data_dir}. "
              f"Run data/generate_test_data.py first or pass --data-dir.",
              file=sys.stderr)
        return 1

    print(f"Loading model registry…")
    print(f"Test data dir: {args.data_dir}")
    print(f"Max rows per model: {args.rows if args.rows > 0 else 'ALL'}")
    print(f"Include explanations: {args.explain}")
    print()

    report = evaluate(
        data_dir=args.data_dir,
        model_filter=args.models,
        max_rows=args.rows,
        include_explanation=args.explain,
    )

    args.report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = args.report_dir / f"evaluation_{ts}.json"
    json_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nJSON report:     {json_path}")

    if not args.no_markdown:
        md_path = args.report_dir / f"evaluation_{ts}.md"
        md_path.write_text(render_markdown(report))
        print(f"Markdown report: {md_path}")

    # Console summary
    n_ok = sum(r.get("n_success", 0) for r in report["results"])
    n_total = sum(r.get("n_rows", 0) for r in report["results"])
    n_failing = sum(
        1 for r in report["results"]
        if r.get("n_runtime_errors", 0) or r.get("n_validation_errors", 0)
    )
    rate = (n_ok / n_total) if n_total else 0.0
    print(f"\nSummary: {n_ok}/{n_total} predictions succeeded ({rate:.1%}); "
          f"{n_failing} model(s) had at least one error.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
