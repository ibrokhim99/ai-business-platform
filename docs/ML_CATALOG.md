# ML Model Catalog

55 production models across 10 blocks. All models: `version=1.0.0`, `is_stub=false`.

---

## Block A — Market Analysis & Capacity

### M-A1 — Market Sizing (TAM/SAM/SOM)
- **Algorithm**: Bayesian bottom-up with `scipy.stats.norm` confidence intervals
- **Input**: region_id, mcc_code, population, avg_income, niche
- **Output**: tam, sam, som, confidence_interval [low, high], methodology
- **Logic**: TAM = population × avg_income × MCC penetration rate (5812→15%, 5411→12%, 5912→8%). SAM = TAM × 0.40, SOM = SAM × 0.25. CI from log-normal distribution.
- **Explain**: population_weight, income_weight, penetration_rate

### M-A2 — GAP Analysis
- **Algorithm**: Normative density calculation + `scipy.stats.poisson` significance test
- **Input**: region_id, mcc_code, normative_density, actual_count, population
- **Output**: normative_count, actual_count, gap, gap_pct, verdict (underserved/balanced/oversaturated)
- **Logic**: normative_count = population/10000 × normative_density. gap = normative − actual. Poisson test for statistical significance.
- **Explain**: normative_density_weight, population_scale_weight

### M-A3 — Saturation Index
- **Algorithm**: Sigmoid-normalised composite index
- **Input**: region_id, mcc_code, competitor_count, population, avg_revenue_per_outlet
- **Output**: saturation_index (0–100), level (low/medium/high/critical), components dict
- **Logic**: outlet_density = competitors / (population/10000). Sigmoid normalisation. Revenue concentration factor. Thresholds: <25=low, <50=medium, <75=high, ≥75=critical.
- **Explain**: density_component, revenue_component

### M-A4 — Wallet Share Estimator
- **Algorithm**: Gravity-adjusted Herfindahl share model
- **Input**: region_id, mcc_code, population, avg_monthly_spend, competitor_count
- **Output**: wallet_share_pct, estimated_monthly_revenue, confidence (0–1)
- **Logic**: wallet_share = 1/(1 + competitors) × MCC_rate × gravity_adjustment. confidence = 0.95 − competitors × 0.05.
- **Explain**: competition_discount, mcc_affinity, gravity_factor

### M-A5 — Niche Opportunity Score
- **Algorithm**: XGBoost regressor trained on 500 synthetic samples
- **Input**: region_id, mcc_code, population, avg_income, competitor_count, growth_rate_pct
- **Output**: opportunity_score (0–100), rank (excellent/good/moderate/poor), top_factors dict
- **Logic**: Features: [population_norm, income_norm, competitor_density, growth_rate]. XGBoost fitted once at class level (seed=42). Returns gain-based feature importances.
- **Explain**: XGBoost gain importances for all 4 features

### M-A6 — Cross-Niche Cannibalization
- **Algorithm**: MCC category graph + haversine distance decay
- **Input**: new_mcc_code, location_lat, location_lon, radius_m, adjacent_mcc_codes
- **Output**: cannibalization_risk (0–1), affected_niches list, net_revenue_impact_pct, recommendation
- **Logic**: 40+ MCC codes mapped to groups. Same-group adjacency = high risk, adjacent-group = medium, unrelated = low. Distance decay applied per affected niche.
- **Explain**: mcc_similarity_weight, distance_decay_weight, group_overlap_weight

---

## Block B — Forecasting & Demand

### M-B1 — Demand Forecasting
- **Algorithm**: Holt-Winters ExponentialSmoothing (additive trend + seasonal, period=12)
- **Input**: region_id, mcc_code, horizon_months (1–36), base_monthly_revenue
- **Output**: forecast list [{month, predicted, lower, upper}], trend, cagr_pct, model_used
- **Logic**: Generates 24 months of synthetic history with MCC-specific growth bias. Fits `statsmodels.tsa.holtwinters.ExponentialSmoothing`. 90% prediction intervals.
- **Explain**: trend_weight, seasonal_weight, base_weight

### M-B2 — Seasonality Model
- **Algorithm**: STL-style decomposition with Uzbekistan-specific calendar events
- **Input**: mcc_code, region_id, year
- **Output**: monthly_indices [12 floats], peak_months, trough_months, events list
- **Logic**: Base pattern adjusted by MCC category. Ramadan month computed per year (lookup table 2024–2030). 7 named events: Navro'z (March), Eid al-Fitr, Eid al-Adha, wedding seasons (May–June, Sep–Oct), New Year.
- **Explain**: base_seasonality, event_adjustments, mcc_modifier

### M-B3 — Population Dynamics
- **Algorithm**: Cohort-component demographic model
- **Input**: region_id, horizon_years (1–20)
- **Output**: projections [{year, population, working_age_pct}], growth_rate_annual_pct, demographic_shift
- **Logic**: Growth rate seeded from region_id hash → range 1.5%–3.5%. working_age_pct starts at 65%, increases 0.15%/year (urbanisation trend). 14 Uzbekistan regions recognised.
- **Explain**: base_growth_rate, urbanisation_trend, regional_coefficient

### M-B4 — Income Trend Forecast
- **Algorithm**: ARIMA(1,1,1) via `statsmodels.tsa.arima.ARIMA`
- **Input**: region_id, horizon_months (3–36), current_avg_income
- **Output**: forecast [{month, avg_income, lower, upper}], real_growth_rate_pct, inflation_adjusted=true
- **Logic**: Fits ARIMA on synthetic income history seeded by region_id. Applies macro parameters: 12.8% nominal, 9.2% inflation → 3.6% real growth.
- **Explain**: trend_component, ar_coefficient, ma_coefficient

### M-B5 — MCC Trend Detector
- **Algorithm**: `ruptures.Pelt` changepoint detection (rbf kernel)
- **Input**: mcc_code, region_id, lookback_months (6–60)
- **Output**: trend_direction (growing/declining/stable/volatile), changepoints [{date, type, magnitude}], momentum_score (-1 to 1), forecast_3m_pct
- **Logic**: Generates synthetic MCC revenue series with MCC-specific growth rates. PELT changepoint detection. Momentum = normalised recent slope.
- **Explain**: momentum_score, changepoint_count, recent_slope

### M-B6 — Business Registration Forecast
- **Algorithm**: `statsmodels.tsa.ar_model.AutoReg(lags=3)` + XGBoost
- **Input**: region_id, mcc_code, horizon_months (3–24)
- **Output**: forecast [{month, new_registrations, cumulative}], annual_growth_pct, competition_intensity
- **Logic**: AutoReg on Poisson-distributed synthetic registration history. MCC-specific base rates and growth multipliers. Competition intensity derived from registration acceleration.
- **Explain**: ar_coefficient, mcc_base_rate, region_multiplier

---

## Block C — Location Assessment & Traffic

### M-C1 — Location Score
- **Algorithm**: 8-factor weighted composite index
- **Input**: lat, lon, mcc_code, radius_m
- **Output**: score (0–100), grade (A/B/C/D/F), sub_scores dict (8 keys), recommendation
- **Logic**: Sub-scores: traffic, competition, vitality, anchor, visibility, isochrone, demographic, income. MCC-specific weight overrides (restaurants weight traffic/anchor more; grocery weights isochrone/demographic). Grade: ≥90=A, ≥80=B, ≥70=C, ≥60=D, else=F.
- **Explain**: weight per sub-score

### M-C2 — Traffic Scoring
- **Algorithm**: `sklearn.GradientBoostingRegressor` trained on 2000 synthetic GPS+time samples
- **Input**: lat, lon, radius_m
- **Output**: daily_foot_traffic, daily_auto_traffic, peak_hours, peak_days, hourly_profile [24 floats], seasonal_factor
- **Logic**: Features: [lat_norm, lon_norm, hour/23, dow/6]. Model trained once at class level (seed=0). Returns predictions for all 24 hours of day. M-C2 is never Redis-cached (always live).
- **Explain**: GradientBoosting feature importances

### M-C3 — Isochrone Demand
- **Algorithm**: Circular isochrone approximation + gravity model
- **Input**: lat, lon, walk_minutes [list], mcc_code
- **Output**: zones [{minutes, area_sqkm, population, consumer_potential_usd}], total_addressable_population, total_consumer_potential_usd
- **Logic**: Walking speed = 1.2 m/s. area = π × r². Population density estimated from distance to Tashkent centroid. MCC-specific daily spend and penetration rates.
- **Explain**: area_weight, density_weight, penetration_weight

### M-C4 — Street Vitality Index
- **Algorithm**: Spatial hash → density tier classification + POI estimation
- **Input**: lat, lon, radius_m
- **Output**: vitality_index (0–100), active_storefronts, vacant_storefronts, poi_count, dominant_categories
- **Logic**: Three density tiers (urban core/suburban/rural) with matching POI densities, vacancy rates, category lists. Spatial hash for within-tier variation.
- **Explain**: active_share_weight, poi_density_weight, vacancy_penalty

### M-C5 — Anchor Effect Model
- **Algorithm**: Newton gravity model (G = mass / d²)
- **Input**: lat, lon, radius_m
- **Output**: anchor_boost_pct, anchors [{name, type, distance_m, gravity_score}], dominant_anchor
- **Logic**: 12 synthetic anchor types (malls, bazaars, hospitals, transit hubs, mosques, universities). Haversine distances. anchor_boost = Σ gravity contributions capped at 80%.
- **Explain**: gravity_mass_weight, distance_decay_power

### M-C6 — Visibility Score
- **Algorithm**: Geometric analysis using trigonometry
- **Input**: lat, lon, facade_direction_deg
- **Output**: visibility_score (0–100), road_frontage_m, sidewalk_width_m, sight_lines dict, obstructions list
- **Logic**: Road frontage and sidewalk width estimated from lat/lon trigonometric hash. Sight lines per compass direction accounting for facade angle. Obstruction pool sampled by location tier.
- **Explain**: frontage_weight, sight_line_weight, direction_bonus

---

## Block D — Financial Viability

### M-D1 — Viability Check
- **Algorithm**: Monte Carlo simulation (500 runs, 24 months)
- **Input**: mcc_code, region_id, monthly_revenue_estimate, monthly_fixed_costs, initial_investment, monthly_rent
- **Output**: survival_probability_2y (0–1), verdict (viable/marginal/high_risk), key_risks list, monthly_break_even, months_to_break_even
- **Logic**: Each run perturbs revenue (−20% to +30%) and costs (±15% σ). Applies 12-month seasonal pattern. MCC-specific base survival priors (restaurants −5%, pharmacy +5%). Survival = fraction of runs with cumulative profit > 0 at month 24. Seed from input values for reproducibility.
- **Explain**: revenue_sensitivity, cost_volatility, mcc_risk_prior

### M-D2 — Unit Economics
- **Algorithm**: Cohort LTV analysis
- **Input**: mcc_code, avg_transaction_value, monthly_transactions, customer_acquisition_cost, monthly_churn_rate_pct, gross_margin_pct
- **Output**: ltv, cac, ltv_cac_ratio, payback_months, net_margin_pct, unit_economics_grade
- **Logic**: LTV = (avg_transaction × monthly_txn × margin%) / churn_rate. MCC-specific opex ratios for net margin (restaurants 70%, software 45%). Grade by LTV/CAC: A ≥ 3, B ≥ 2, C ≥ 1, D ≥ 0.5, else F.
- **Explain**: ltv_driver, churn_impact, margin_component

### M-D3 — ROI Estimator
- **Algorithm**: DCF + `scipy.optimize.brentq` for exact IRR
- **Input**: initial_investment, monthly_net_cash_flow, discount_rate_annual_pct, horizon_years
- **Output**: npv, irr_pct, payback_months, roi_pct, verdict
- **Logic**: NPV = Σ(CF/(1+r)^t) − I. IRR via brentq searching monthly rate space [1e-8, 5.0]. Fractional payback interpolation. Verdict: positive NPV + IRR > discount = "strong", NPV positive = "viable", else "loss".
- **Explain**: npv_sensitivity, payback_efficiency, irr_vs_hurdle

### M-D4 — Rental Burden Model
- **Algorithm**: MCC-calibrated threshold model
- **Input**: mcc_code, monthly_revenue_estimate, monthly_rent
- **Output**: rent_to_revenue_pct, safe_threshold_pct, critical_threshold_pct, status (safe/warning/critical), max_affordable_rent
- **Logic**: MCC-specific thresholds: restaurants safe=15%/critical=25%, grocery safe=10%/critical=18%, software safe=25%/critical=40%. Status based on ratio vs thresholds.
- **Explain**: mcc_threshold_adjustment, revenue_base_weight

### M-D5 — Cash Flow Simulator
- **Algorithm**: Monte Carlo cash flow (500 simulations, P50 scenario)
- **Input**: mcc_code, region_id, initial_investment, monthly_revenue_base, monthly_fixed_costs, cogs_pct, growth_rate_monthly_pct, horizon_months
- **Output**: monthly_cashflows [{month, revenue, costs, net_cashflow, cumulative}], total_net, cash_gap_months, break_even_month, final_balance
- **Logic**: 500 runs. Revenue = base × (1+growth)^m × seasonality × N(1, MCC_std). costs = fixed + cogs%×revenue. Returns P50 scenario. cash_gap_months = months where cumulative < 0.
- **Explain**: growth_sensitivity, seasonality_impact, cogs_pressure

### M-D6 — COGS & Margin Estimator
- **Algorithm**: MCC benchmark lookup + region and scale adjustments
- **Input**: mcc_code, monthly_revenue, region_id
- **Output**: cogs_pct, gross_margin_pct, operating_margin_pct, net_margin_pct, benchmark_source, industry_comparison
- **Logic**: 20+ MCC benchmark entries. Tashkent region cost index +5–8%. Revenue scale effect (+2.5% margin per $100k/month). industry_comparison vs median benchmark.
- **Explain**: mcc_benchmark, region_cost_adjustment, scale_effect

---

## Block E — Competition & Risks

### M-E1 — Competitor Intelligence
- **Algorithm**: Haversine spatial query with MD5-seeded deterministic generation
- **Input**: lat, lon, mcc_code, radius_300m, radius_1km
- **Output**: competitors_300m list, competitors_1km list, total_count, avg_rating, market_leader, threat_level
- **Logic**: Competitor count/positions seeded from MD5(mcc_code + lat_rounded + lon_rounded). 0–3 competitors within 300m, 0–8 within 1km. threat_level based on count: <2=low, <5=medium, <8=high, ≥8=critical.
- **Explain**: density_factor, proximity_weight, market_concentration

### M-E2 — Churn Prediction
- **Algorithm**: XGBoost classifier (1000 synthetic samples) + Kaplan-Meier survival curve
- **Input**: mcc_code, region_id, monthly_revenue, initial_investment, owner_experience_years, location_score, competition_count
- **Output**: closure_probability_2y (0–1), risk_level (low/medium/high), top_risk_factors, survival_curve [{month, survival_probability}]
- **Logic**: Features: [revenue_to_investment_ratio, owner_experience_norm, location_score_norm, competition_density, mcc_risk_factor]. Survival curve via `scipy.stats.expon.sf()`.
- **Explain**: XGBoost feature importances

### M-E3 — Regulatory Risk Score
- **Algorithm**: Rule-based MCC regulatory classifier (17 categories)
- **Input**: mcc_code, region_id, business_age_months
- **Output**: risk_score (0–100), risk_level (low/medium/high), applicable_regulations, inspection_frequency, common_violations
- **Logic**: MCC → regulatory category (food safety, pharmaceutical, financial, etc.). Base risk per category. Age reduction (−1.5 per year, max −15). Region multiplier.
- **Explain**: regulatory_category_weight, age_reduction, region_multiplier

### M-E4 — Market Entry Barrier Index
- **Algorithm**: Weighted composite (5 components)
- **Input**: mcc_code, region_id, initial_investment
- **Output**: barrier_index (0–100), barrier_level (low/medium/high/very_high), components dict, recommendation
- **Logic**: Components: capital(40) + regulatory(30) + brand_loyalty(15) + economies_of_scale(10) + switching_costs(5). Each weighted by MCC-specific coefficients.
- **Explain**: weight per component

### M-E5 — Price Pressure Model
- **Algorithm**: Hedonic pricing + MCC-specific price elasticity
- **Input**: mcc_code, region_id, target_price, competitor_avg_price
- **Output**: price_pressure_score (0–1), optimal_price_range [min, max], price_elasticity, recommended_price, margin_at_recommended
- **Logic**: Elasticity range −0.9 to −2.5 by MCC. Optimal range: [competitor×0.90, competitor×1.10]. price_pressure = |target − competitor| / competitor.
- **Explain**: elasticity_coefficient, competitive_gap, region_price_index

---

## Block F — Credit & Banking Products

### M-F1 — Credit Risk Score
- **Algorithm**: LightGBM classifier trained on 2000 synthetic samples
- **Input**: customer_id, mcc_code, region_id, lat, lon, monthly_revenue_estimate, requested_loan_amount, business_age_months, owner_credit_history_score, collateral_value
- **Output**: credit_score (0–1000), risk_grade (AAA/AA/A/BBB/BB/B/CCC), default_probability (0–1), max_recommended_loan, decision (approve/conditional/reject), conditions list
- **Logic**: 6 features: [credit_hist_norm, revenue_coverage_ratio, age_norm, collateral_ratio, location_risk, mcc_risk]. LightGBM trained with seed=42. Score bands: ≥800=AAA/approve, ≥700=AA, ≥600=A, ≥500=BBB/conditional, ≥400=BB, ≥300=B/reject, else=CCC.
- **Explain**: LightGBM feature importances (gain)

### M-F2 — Loan Sizing Recommender
- **Algorithm**: Standard annuity formula + 43% DTI constraint
- **Input**: monthly_net_cashflow, monthly_revenue, existing_debt_monthly, loan_term_months, interest_rate_annual_pct
- **Output**: recommended_loan, max_loan, monthly_payment, dti_ratio, affordability_verdict
- **Logic**: monthly_payment = L × r(1+r)^n / ((1+r)^n − 1). max_loan via DTI=43% constraint. recommended = min(max_loan, 2.5 × annual_revenue) × 0.80.
- **Explain**: dti_constraint_weight, cashflow_coverage_weight, term_factor

### M-F3 — DTI Predictor
- **Algorithm**: MCC-specific revenue growth projection + annuity payment
- **Input**: mcc_code, region_id, initial_monthly_revenue, proposed_loan_amount, loan_term_months, interest_rate_annual_pct
- **Output**: dti_at_6m, dti_at_12m, dti_at_24m, safe_threshold=0.43, risk_periods, trajectory
- **Logic**: MCC-specific monthly growth rates (0.7%–1.5%). Revenue projected at 6/12/24m. DTI = monthly_payment / projected_revenue. trajectory: declining DTI = improving, else deteriorating.
- **Explain**: growth_rate_assumption, payment_to_revenue_ratio

### M-F4 — NPL Early Warning
- **Algorithm**: `sklearn.IsolationForest` + rule-based adjustment layer
- **Input**: customer_id, loan_id, months_since_disbursement, payment_delays_count, revenue_trend_3m_pct, current_dti, location_score
- **Output**: npl_probability (0–1), alert_level (green/yellow/orange/red), days_to_potential_default, recommended_actions, anomaly_flags
- **Logic**: IsolationForest trained on 1000 synthetic healthy-loan samples. Rule adjustments: +0.20 per delay, +0.15 if DTI > 0.6, +0.10 if revenue trend < −10%. alert: <0.20=green, <0.40=yellow, <0.65=orange, else=red. M-G2 never Redis-cached.
- **Explain**: anomaly_score, payment_delay_penalty, dti_risk_flag

### M-F5 — Bank Product Recommender
- **Algorithm**: Content-based collaborative filtering
- **Input**: customer_id, mcc_code, monthly_revenue, business_age_months, existing_products, credit_score
- **Output**: recommendations [{product, type, score, rationale, amount_range}], primary_recommendation, cross_sell_opportunities
- **Logic**: 7 products: business_loan, overdraft, leasing, bank_guarantee, factoring, deposit, pos_terminal. Score = credit_score × revenue × age affinity × MCC_weight, normalised. Filters out existing_products. Returns top 3.
- **Explain**: credit_score_weight, revenue_affinity, mcc_product_match

---

## Block G — Social Profile & Audience

### M-G1 — Customer Segment Profiler
- **Algorithm**: K-means (k=4) trained on 1000 synthetic samples
- **Input**: lat, lon, radius_m, mcc_code
- **Output**: segments [{segment_id, label, share_pct, avg_age, avg_income, top_categories, visit_frequency}], dominant_segment, total_addressable_customers
- **Logic**: 4 segments: "Young Urban" (22–35, high freq), "Family Shoppers" (30–45, medium), "Premium Buyers" (35–55, low freq high spend), "Budget Conscious" (25–50, high freq low spend). Share_pct from IDW distances. total_addressable = π×(r/1000)² × 8000.
- **Explain**: cluster_distance_weights, mcc_segment_affinity

### M-G2 — Day Population Estimator
- **Algorithm**: Gravity model with 24-hour weekday/weekend profiles
- **Input**: lat, lon, radius_m, hour_of_day (0–23), day_of_week (0–6)
- **Output**: residents, workers, visitors, transit_passers, total_population, hourly_profile [24 ints]
- **Logic**: base_population = π×(r/1000)² × 8000. residents=60%. Workers peak 8–18 on weekdays. Visitors/transit vary by hour + day. M-G2 is never Redis-cached (always live).
- **Explain**: resident_base_weight, worker_profile_hour, visitor_day_multiplier

### M-G3 — Consumer Behavior Classifier
- **Algorithm**: MCC-based rule engine with 4 consumer type profiles
- **Input**: lat, lon, radius_m, mcc_code
- **Output**: consumer_types [{type, share_pct, peak_hours, avg_spend, description}], dominant_type, marketing_insight
- **Logic**: MCC lookup table: 5812→[morning coffee crowd, lunch crowd, evening diners], 5411→[morning shoppers, evening grocers], 5912→[health-conscious, elderly]. Default fallback profile.
- **Explain**: mcc_type_affinity, location_modifier

### M-G4 — Brand Affinity Model
- **Algorithm**: Urban-score via haversine from Uzbek city centres
- **Input**: lat, lon, radius_m, mcc_code
- **Output**: chain_preference_pct (0–100), independent_preference_pct (0–100), top_chains, brand_loyalty_index (0–1), opportunity_type (chain/independent/mixed)
- **Logic**: chain_pct scales 20–80% by proximity to Tashkent, Samarkand, Namangan. top_chains by MCC (5812→["Dodo Pizza","Burger House","Coffee House"]). loyalty_index = chain_pct/100 × 0.80.
- **Explain**: urban_proximity_score, chain_density_index

### M-G5 — Spending Power Index
- **Algorithm**: Inverse-Distance Weighting (IDW) spatial interpolation
- **Input**: lat, lon, radius_m
- **Output**: spending_power_index (0–100), avg_monthly_spend_per_capita, quartile (Q1/Q2/Q3/Q4), heatmap_cells [{lat, lon, index}], category_breakdown dict
- **Logic**: IDW from 5 urban reference points with known spending indices. 5×5 heatmap grid generated within radius. avg_monthly_spend = 150 + index × 5 (USD). Quartile by index value.
- **Explain**: idw_weights, reference_point_distances

---

## Block H — Marketing & Customer Acquisition

### M-H1 — CAC Predictor
- **Algorithm**: GradientBoostingRegressor on channel × region × MCC × budget (2000-sample training)
- **Input**: channel, region_id, monthly_budget, industry_mcc, target_segment, historical_cac, competition_intensity
- **Output**: predicted_cac, cac_range_low/high, expected_acquisitions, channel_efficiency, drivers
- **Logic**: Channel/region/MCC baselines × budget scale-economy term × competition intensity. If `historical_cac > 0`, blend 70/30 with model output for Bayesian shrinkage.
- **Explain**: GBR feature importances normalized to weights

### M-H2 — LTV / CAC Ratio
- **Algorithm**: Closed-form contractual LTV with monthly discounting + payback period
- **Input**: arpu_monthly, gross_margin_pct, monthly_churn_rate, discount_rate_annual, cac
- **Output**: ltv, ltv_cac_ratio, payback_months, verdict (unsustainable/marginal/healthy/excellent), recommendations
- **Logic**: `LTV = ARPU × margin / (churn + monthly_discount)`. Verdict thresholds: <1, 1–3, 3–5, >5. Payback = `CAC / contribution`.
- **Explain**: ARPU, margin, churn, CAC weights

### M-H3 — Channel Attribution
- **Algorithm**: Shapley value (exact for ≤7 unique touchpoints, Monte Carlo otherwise)
- **Input**: journey_id, touchpoints (ordered list), conversion_value
- **Output**: weights {channel→share}, credit {channel→$}, primary_driver, method
- **Logic**: Cooperative-game value function `v(S) = 1 − ∏(1 − lift_ch)` over subset of channels. Shapley = average marginal contribution over all orderings.
- **Explain**: shapley_marginal_contribution

### M-H4 — Promo Uplift
- **Algorithm**: Two-model uplift (separate treated/control GBM classifiers), CATE = P(buy|T) − P(buy|C)
- **Input**: customer_id, promo_type, promo_value, RFM features (recency/frequency/monetary), historical_response_rate
- **Output**: uplift_probability, treated/control response probs, expected_incremental_revenue, target_decision, segment
- **Logic**: Four-quadrant segmentation: `persuadable` (uplift > 0.05), `sleeping_dog` (uplift < −0.05), `sure_thing` (both ≥ 0.5), `lost_cause` (otherwise). Targets only `persuadable`; suppresses `sleeping_dog`.
- **Explain**: Average feature importances across treated and control models

### M-H5 — Optimal Pricing
- **Algorithm**: Log-log price elasticity → Lerner mark-up `p* = MC × ε / (ε + 1)` for `ε < −1`
- **Input**: product_id, current_price, current_units_sold, unit_cost, elasticity_estimate, optional price_floor/ceiling
- **Output**: optimal_price, expected_units, expected_revenue, expected_margin, revenue_lift_pct, margin_lift_pct, confidence
- **Logic**: Constant-elasticity demand `Q(p) = Q0 × (p/p0)^ε`. Inelastic case (ε ≥ −1) recommends +25% (capped by ceiling). Floor/ceiling enforced.
- **Explain**: elasticity, unit_cost, current_price weights

### M-H6 — Lookalike Audience
- **Algorithm**: Cosine-similarity k-NN over numeric feature vectors
- **Input**: seed_customer_features (dict), candidate_pool (list of dicts), top_k
- **Output**: matches [{customer_id, similarity}], avg_similarity, seed_features_used
- **Logic**: Uses intersection of numeric keys in seed for vectorization; cosine sim over standardized vectors; sort desc; top_k.
- **Explain**: cosine_similarity (single feature)

---

## Block I — Operations & Supply Chain

### M-I1 — Inventory Optimizer
- **Algorithm**: EOQ + (s, S) policy with normal-approximation safety stock
- **Input**: sku_id, annual_demand, unit_cost, ordering_cost, holding_cost_pct, lead_time_days, demand_std_daily, service_level
- **Output**: economic_order_quantity, reorder_point, safety_stock, annual_orders, total_annual_cost, target_service_level
- **Logic**: `EOQ = sqrt(2DK/h)`; safety = `z(SL) × σ_LT`; reorder point = `μ_LT + safety`. Total cost = ordering + holding + safety holding.
- **Explain**: annual_demand 0.40, ordering_cost 0.20, holding 0.20, lead_time 0.10, service_level 0.10

### M-I2 — Stockout Risk
- **Algorithm**: Normal-approximation demand × lead-time tail probability
- **Input**: sku_id, on_hand_units, on_order_units, daily demand mean/std, lead-time mean/std, horizon_days
- **Output**: stockout_probability, expected_stockout_days, days_of_cover, risk_level, recommended_action
- **Logic**: Cumulative demand over (horizon + LT) ≈ Normal(μ×T, σ×√T). Stockout probability = `1 − Φ((available − μ)/σ)`. Combines demand variance + lead-time variance.
- **Explain**: available_inventory 0.40, demand_rate 0.30, demand_volatility 0.15, lead_time 0.15

### M-I3 — Supplier Risk Score
- **Algorithm**: Weighted multi-factor rule scorer
- **Input**: supplier_id, months_active, on_time_delivery_rate, quality_defect_rate, payment_delay_avg_days, revenue_concentration_pct, single_source_flag, geopolitical_risk
- **Output**: risk_score (0–1000), risk_band, primary_risk_factor, contingency_actions
- **Logic**: Weights — delivery 0.22, quality 0.18, concentration 0.18, geopolitical 0.15, single_source 0.12, payment 0.10, tenure 0.05. Band thresholds: <250 low, <500 medium, <750 high, ≥750 severe.
- **Explain**: Per-factor weighted contributions

### M-I4 — Staffing Optimizer
- **Algorithm**: Per-hour demand → ceil(staff slots) with min/max bounds and open/close gating
- **Input**: location_id, hourly_demand (length 24), units_per_staff_hour, min/max staff, open/close hours, hourly_wage
- **Output**: hourly_staff (length 24), total_staff_hours, estimated_labor_cost, peak_hour, peak_hour_staff
- **Logic**: For each open hour: `staff_h = clip(ceil(demand_h / units_per_staff_hour), min, max)`. Closed hours = 0. Supports overnight schedules via wrap-around.
- **Explain**: hourly_demand 0.60, units_per_staff_hour 0.20, min_max_constraints 0.20

### M-I5 — Delivery Routing (VRP)
- **Algorithm**: Clarke-Wright savings heuristic with capacity constraint (haversine distance)
- **Input**: depot_lat/lon, stops [{stop_id, lat, lon, demand}], vehicle_capacity, n_vehicles
- **Output**: routes [{vehicle_id, stop_sequence, distance_km, load}], total_distance_km, n_vehicles_used, unrouted_stops
- **Logic**: Each stop starts as own out-and-back route; greedily merge by largest savings `s_ij = d(0,i) + d(0,j) − d(i,j)` while respecting capacity. Overflow stops returned as `unrouted`.
- **Explain**: stop_geography 0.50, vehicle_capacity 0.30, fleet_size 0.20

---

## Block J — Fraud, AML & Identity

> **Caching:** All Block J models bypass the Redis prediction cache (`_NO_CACHE`) so fraud signals always reflect current state.

### M-J1 — Transaction Anomaly Detection
- **Algorithm**: IsolationForest on amount/velocity/MCC features (3000-sample training) + rule overlay
- **Input**: customer_id, transaction_id, amount, mcc_code, velocity (24h/7d), avg_amount_30d, distinct_merchants_24h, is_foreign, is_cnp, hour_of_day
- **Output**: anomaly_score (0–1), is_anomaly, risk_level (low/medium/high/critical), triggered_rules, recommended_action
- **Logic**: Sigmoid-mapped IsolationForest score (calibrated: normal ~0.10, outlier ~0.55) + rule adjustments (5× avg amount, >15 txns/24h, foreign+CNP, odd-hour large).
- **Explain**: amount_zscore 0.30, velocity_24h 0.25, foreign_cnp 0.20, distinct_merchants 0.15, odd_hour 0.10

### M-J2 — Merchant Fraud Score
- **Algorithm**: LightGBM classifier on chargeback/velocity/tenure + MCC fraud-prior (2000-sample training)
- **Input**: merchant_id, mcc_code, months_active, chargeback_rate_30d, refund_rate_30d, avg_ticket_size, txn_velocity_per_day, pct_cnp/foreign, prior_complaints_count
- **Output**: fraud_score (0–1000), fraud_probability, risk_band (low/medium/high/severe), decision (monitor/restrict/suspend), risk_factors
- **Logic**: GBM probability → 0–1000 score. Decision: <0.50 monitor, <0.75 restrict, ≥0.75 suspend. MCC priors elevate gambling (0.70), digital goods (0.60), telemarketing (0.65).
- **Explain**: LightGBM feature importances normalized

### M-J3 — AML Suspicious Pattern Detection
- **Algorithm**: Rule-based typology scorer (FATF structuring/layering heuristics)
- **Input**: customer_id, cash deposit metrics (count/amount/near-threshold), rapid in-out cycles, distinct counterparties, cross-border + high-risk-jurisdiction counts
- **Output**: suspicion_score (0–1), typology (structuring/layering/integration/none), sar_recommended, triggered_typologies, confidence
- **Logic**: Three independent typology scores; dominant becomes the assigned typology. SAR recommended when `suspicion ≥ 0.55`. Confidence = top score − second + 0.5 (capped at 1).
- **Explain**: structuring 0.40, layering 0.30, cross_border 0.20, high_risk_jurisdiction 0.10

### M-J4 — Synthetic Identity Detection
- **Algorithm**: XGBoost classifier on credit-thinness + identity-tenure features (2000-sample training)
- **Input**: applicant_id, credit_file_age_months, credit_inquiries_last_6m, address_changes_24m, ssn_age_norm, phone/email tenure, distinct_names_at_address, employer_verifiable
- **Output**: synthetic_probability (0–1), is_synthetic, confidence_band (low/medium/high), contributing_factors, verification_steps
- **Logic**: Thin file + high inquiry velocity + identity-document age inconsistent with applicant age + address sharing → synthetic. Verification steps escalate from "standard KYC" to "in-person" by band.
- **Explain**: XGBoost feature importances normalized

### M-J5 — Application Fraud Detection
- **Algorithm**: GradientBoosting on application-velocity + identity-overlap features (2000-sample training)
- **Input**: application_id, applications_24h/30d, device/IP shared count_30d, declared_income vs bureau_income_estimate, document_quality_score, velocity_score, geolocation_mismatch
- **Output**: fraud_probability, decision (approve/review/deny), fraud_indicators, income_discrepancy_pct, risk_score (0–1000)
- **Logic**: Decision thresholds: <0.30 approve, <0.65 review, ≥0.65 deny. Income discrepancy = `(declared − bureau) / bureau`. Indicators surface velocity bursts, device sharing, doc tampering, geo mismatch.
- **Explain**: GBM feature importances normalized
