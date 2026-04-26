// ── Core response wrapper ──────────────────────────────────────────────────

export interface PredictionResponse<T = Record<string, unknown>> {
  model_id: string;
  version: string;
  is_stub: boolean;
  prediction: T;
  explanation: ExplanationResult | null;
  latency_ms: number;
  request_id: string;
}

export interface ExplanationResult {
  shap_values?: Record<string, number>;
  feature_importance?: Record<string, number>;
  summary?: string;
  [key: string]: unknown;
}

// ── User ───────────────────────────────────────────────────────────────────

export interface User {
  email: string;
  role: 'admin' | 'analyst' | 'credit_officer' | 'user';
}

// ── Block A: Market Analysis ───────────────────────────────────────────────

export interface MarketSizingInput {
  region_id: string;
  mcc_code: string;
  population: number;
  avg_income: number;
  niche: string;
}

export interface MarketSizingOutput {
  total_addressable_market: number;
  serviceable_market: number;
  market_penetration_rate: number;
  estimated_annual_revenue: number;
  currency: string;
}

export interface GapAnalysisInput {
  region_id: string;
  mcc_code: string;
  normative_density: number;
  actual_count: number;
  population: number;
}

export interface GapAnalysisOutput {
  gap_score: number;
  supply_deficit: number;
  demand_excess: number;
  opportunity_rating: string;
  recommended_outlets: number;
}

export interface SaturationIndexInput {
  region_id: string;
  mcc_code: string;
  competitor_count: number;
  population: number;
  avg_revenue_per_outlet: number;
}

export interface SaturationIndexOutput {
  saturation_index: number;
  market_status: string;
  revenue_pressure: number;
  entry_difficulty: string;
}

export interface WalletShareInput {
  region_id: string;
  mcc_code: string;
  population: number;
  avg_monthly_spend: number;
  competitor_count: number;
}

export interface WalletShareOutput {
  wallet_share_pct: number;
  capturable_revenue_monthly: number;
  avg_spend_per_customer: number;
  market_concentration: string;
}

export interface NicheOpportunityInput {
  region_id: string;
  mcc_code: string;
  population: number;
  avg_income: number;
  competitor_count: number;
  growth_rate_pct: number;
}

export interface NicheOpportunityOutput {
  opportunity_score: number;
  niche_attractiveness: string;
  growth_potential: number;
  risk_level: string;
  recommended_action: string;
}

export interface CrossNicheInput {
  new_mcc_code: string;
  location_lat: number;
  location_lon: number;
  radius_m: number;
  adjacent_mcc_codes: string[];
}

export interface CrossNicheOutput {
  synergy_score: number;
  top_synergies: Array<{ mcc_code: string; synergy: number; description: string }>;
  cross_sell_potential: number;
  recommended_combinations: string[];
}

// ── Block B: Forecasting ───────────────────────────────────────────────────

export interface DemandForecastInput {
  region_id: string;
  mcc_code: string;
  horizon_months: number;
  base_monthly_revenue: number;
}

export interface DemandForecastOutput {
  forecasts: Array<{ month: number; predicted: number; lower: number; upper: number }>;
  trend: string;
  cagr: number;
}

export interface SeasonalityInput {
  mcc_code: string;
  region_id: string;
  year: number;
}

export interface SeasonalityOutput {
  monthly_indices: number[];
  peak_month: number;
  trough_month: number;
  seasonality_strength: number;
}

export interface PopulationDynamicsInput {
  region_id: string;
  horizon_years: number;
}

export interface PopulationDynamicsOutput {
  projections: Array<{ year: number; population: number; growth_rate: number }>;
  net_migration: number;
  demographic_index: number;
}

export interface IncomeTrendInput {
  region_id: string;
  mcc_code: string;
  horizon_months: number;
}

export interface IncomeTrendOutput {
  trend_direction: string;
  cagr: number;
  projected_avg_income: number;
  confidence: number;
}

export interface MccTrendInput {
  mcc_code: string;
  region_id: string;
  horizon_months: number;
}

export interface MccTrendOutput {
  trend_score: number;
  momentum: string;
  volume_change_pct: number;
  emerging_flag: boolean;
}

export interface BusinessRegistrationInput {
  region_id: string;
  mcc_code: string;
  horizon_months: number;
}

export interface BusinessRegistrationOutput {
  new_registrations_forecast: number;
  churn_forecast: number;
  net_growth: number;
  sector_health: string;
}

// ── Block C: Location Assessment ──────────────────────────────────────────

export interface LocationScoreInput {
  lat: number;
  lon: number;
  mcc_code: string;
  radius_m: number;
}

export interface LocationScoreOutput {
  score: number;
  grade: string;
  foot_traffic_index: number;
  accessibility_score: number;
  competitor_proximity: number;
  recommendation: string;
}

export interface TrafficScoringInput {
  lat: number;
  lon: number;
  radius_m: number;
}

export interface TrafficScoringOutput {
  daily_traffic: number;
  hourly_profile: number[];
  peak_hours: number[];
  traffic_quality: string;
}

export interface IsochroneDemandInput {
  lat: number;
  lon: number;
  travel_time_minutes: number;
  mcc_code: string;
}

export interface IsochroneDemandOutput {
  reachable_population: number;
  demand_score: number;
  coverage_area_km2: number;
  income_profile: string;
}

export interface StreetVitalityInput {
  lat: number;
  lon: number;
  radius_m: number;
}

export interface StreetVitalityOutput {
  vitality_score: number;
  retail_density: number;
  diversity_index: number;
  vacancy_rate: number;
}

export interface AnchorEffectInput {
  lat: number;
  lon: number;
  radius_m: number;
  mcc_code: string;
}

export interface AnchorEffectOutput {
  anchor_score: number;
  nearest_anchors: Array<{ name: string; distance_m: number; type: string }>;
  halo_effect: number;
}

export interface VisibilityScoreInput {
  lat: number;
  lon: number;
  radius_m: number;
}

export interface VisibilityScoreOutput {
  visibility_score: number;
  signage_potential: string;
  street_frontage_m: number;
  pedestrian_exposure: number;
}

// ── Block D: Financial Viability ───────────────────────────────────────────

export interface ViabilityCheckInput {
  region_id: string;
  mcc_code: string;
  monthly_revenue: number;
  monthly_costs: number;
  initial_investment: number;
}

export interface ViabilityCheckOutput {
  survival_probability_2y: number;
  verdict: string;
  break_even_months: number;
  margin_pct: number;
  risk_flags: string[];
}

export interface UnitEconomicsInput {
  avg_transaction_value: number;
  transactions_per_day: number;
  variable_cost_pct: number;
  fixed_costs_monthly: number;
}

export interface UnitEconomicsOutput {
  ltv: number;
  cac: number;
  ltv_cac_ratio: number;
  contribution_margin: number;
  payback_period_months: number;
}

export interface RoiEstimatorInput {
  initial_investment: number;
  annual_revenue: number;
  annual_costs: number;
  discount_rate_pct: number;
  horizon_years: number;
}

export interface RoiEstimatorOutput {
  npv: number;
  irr: number;
  payback_years: number;
  roi_pct: number;
  recommendation: string;
}

export interface RentalBurdenInput {
  monthly_rent: number;
  monthly_revenue: number;
  mcc_code: string;
  region_id: string;
}

export interface RentalBurdenOutput {
  rental_burden_pct: number;
  industry_benchmark_pct: number;
  status: string;
  max_sustainable_rent: number;
}

export interface CashFlowSimulatorInput {
  initial_investment: number;
  monthly_revenue: number;
  monthly_fixed_costs: number;
  variable_cost_pct: number;
  horizon_months: number;
}

export interface CashFlowSimulatorOutput {
  monthly_cashflows: Array<{ month: number; revenue: number; costs: number; net: number; cumulative: number }>;
  break_even_month: number;
  total_return: number;
  peak_negative: number;
}

export interface CogsMarginsInput {
  mcc_code: string;
  region_id: string;
  revenue_monthly: number;
  cogs_monthly: number;
}

export interface CogsMarginsOutput {
  gross_margin_pct: number;
  industry_avg_pct: number;
  margin_gap: number;
  optimization_tips: string[];
}

// ── Block E: Competition & Risks ───────────────────────────────────────────

export interface CompetitorIntelligenceInput {
  region_id: string;
  mcc_code: string;
  radius_m: number;
}

export interface CompetitorIntelligenceOutput {
  competitor_count: number;
  market_leaders: Array<{ name: string; market_share_pct: number; threat_level: string }>;
  competitive_intensity: string;
}

export interface ChurnPredictionInput {
  business_age_months: number;
  monthly_revenue: number;
  transaction_trend: number;
  region_id: string;
  mcc_code: string;
}

export interface ChurnPredictionOutput {
  churn_probability: number;
  risk_level: string;
  key_churn_factors: string[];
  retention_recommendations: string[];
}

export interface RegulatoryRiskInput {
  mcc_code: string;
  region_id: string;
  business_type: string;
}

export interface RegulatoryRiskOutput {
  risk_score: number;
  regulatory_flags: string[];
  compliance_requirements: string[];
  risk_level: string;
}

export interface EntryBarrierInput {
  mcc_code: string;
  region_id: string;
  initial_capital: number;
}

export interface EntryBarrierOutput {
  barrier_score: number;
  barrier_level: string;
  key_barriers: string[];
  time_to_market_months: number;
}

export interface PricePressureInput {
  mcc_code: string;
  region_id: string;
  current_price: number;
  competitor_avg_price: number;
}

export interface PricePressureOutput {
  pressure_index: number;
  pricing_power: string;
  optimal_price_range: { min: number; max: number };
  elasticity_estimate: number;
}

// ── Block F: Credit & Banking ──────────────────────────────────────────────

export interface CreditRiskScoreInput {
  business_age_months: number;
  monthly_revenue: number;
  monthly_expenses: number;
  existing_debt: number;
  mcc_code: string;
  region_id: string;
}

export interface CreditRiskScoreOutput {
  risk_score: number;
  risk_grade: string;
  default_probability: number;
  recommended_rate_pct: number;
}

export interface LoanSizingInput {
  monthly_revenue: number;
  monthly_net_income: number;
  existing_debt_monthly: number;
  collateral_value: number;
  mcc_code: string;
}

export interface LoanSizingOutput {
  max_loan_amount: number;
  recommended_loan_amount: number;
  dti_ratio: number;
  loan_to_value: number;
}

export interface DtiPredictorInput {
  gross_monthly_income: number;
  monthly_debt_payments: number;
  region_id: string;
}

export interface DtiPredictorOutput {
  dti_ratio: number;
  status: string;
  max_additional_payment: number;
  risk_level: string;
}

export interface NplWarningInput {
  loan_id: string;
  days_past_due: number;
  monthly_revenue: number;
  collateral_value: number;
}

export interface NplWarningOutput {
  npl_probability: number;
  alert_level: string;
  recommended_actions: string[];
  recovery_estimate: number;
}

export interface ProductRecommenderInput {
  business_age_months: number;
  monthly_revenue: number;
  mcc_code: string;
  region_id: string;
  risk_grade: string;
}

export interface ProductRecommenderOutput {
  recommended_products: Array<{ product: string; reason: string; priority: number }>;
  cross_sell_score: number;
  upsell_potential: string;
}

// ── Block G: Social Profile ────────────────────────────────────────────────

export interface CustomerProfilerInput {
  lat: number;
  lon: number;
  radius_m: number;
  mcc_code: string;
}

export interface CustomerProfilerOutput {
  segments: Array<{
    segment_name: string;
    percentage: number;
    avg_age: number;
    avg_income: number;
    primary_interests: string[];
  }>;
  dominant_segment: string;
  diversity_score: number;
}

export interface DayPopulationInput {
  lat: number;
  lon: number;
  radius_m: number;
  hour_of_day: number;
  day_of_week: number;
}

export interface DayPopulationOutput {
  total_population: number;
  residents: number;
  workers: number;
  visitors: number;
  density_per_km2: number;
}

export interface BehaviorClassifierInput {
  lat: number;
  lon: number;
  radius_m: number;
  mcc_code: string;
}

export interface BehaviorClassifierOutput {
  dominant_behavior: string;
  behavior_segments: Array<{ behavior: string; percentage: number }>;
  visit_frequency: string;
  spend_propensity: string;
}

export interface BrandAffinityInput {
  lat: number;
  lon: number;
  radius_m: number;
  mcc_code: string;
}

export interface BrandAffinityOutput {
  top_brands: Array<{ brand: string; affinity_score: number }>;
  price_sensitivity: string;
  brand_loyalty_index: number;
}

export interface SpendingPowerInput {
  lat: number;
  lon: number;
  radius_m: number;
  mcc_code: string;
}

export interface SpendingPowerOutput {
  avg_monthly_spend: number;
  spend_percentile: number;
  disposable_income_est: number;
  spending_categories: Record<string, number>;
}
