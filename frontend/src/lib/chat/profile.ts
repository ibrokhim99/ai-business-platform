export interface BusinessProfile {
  region_id: string;
  region_label: string;
  population: number;
  avg_income: number;
  mcc_code: string;
  mcc_label: string;
  niche: string;

  lat: number;
  lon: number;
  radius_m: number;
  walk_minutes: number;
  facade_direction_deg: number;

  monthly_revenue_estimate: number;
  monthly_fixed_costs: number;
  monthly_rent: number;
  initial_investment: number;
  business_age_months: number;
  owner_experience_years: number;
  owner_credit_history_score: number;
  collateral_value: number;

  cogs_pct: number;
  avg_transaction_value: number;
  monthly_transactions: number;
  customer_acquisition_cost: number;
  monthly_churn_rate_pct: number;
  gross_margin_pct: number;
  discount_rate_annual_pct: number;
  horizon_months: number;
  growth_rate_monthly_pct: number;

  requested_loan_amount: number;
  loan_term_months: number;
  interest_rate_annual_pct: number;
  existing_debt_monthly: number;
}

// Profile starts empty — the LLM must call `ask_followup` to gather the
// primary fields (region_id, mcc_code, monthly_revenue_estimate,
// initial_investment) from the user before it can run any models. Secondary
// technical defaults (margins, rates, horizons) remain so model inputs are
// well-formed once the primary fields are filled in.
export const DEFAULT_PROFILE: BusinessProfile = {
  region_id: '',
  region_label: '',
  population: 0,
  avg_income: 0,
  mcc_code: '',
  mcc_label: '',
  niche: '',

  lat: 0,
  lon: 0,
  radius_m: 500,
  walk_minutes: 10,
  facade_direction_deg: 180,

  monthly_revenue_estimate: 0,
  monthly_fixed_costs: 0,
  monthly_rent: 0,
  initial_investment: 0,
  business_age_months: 0,
  owner_experience_years: 3,
  owner_credit_history_score: 680,
  collateral_value: 25_000,

  cogs_pct: 40,
  avg_transaction_value: 15,
  monthly_transactions: 1_000,
  customer_acquisition_cost: 5,
  monthly_churn_rate_pct: 5,
  gross_margin_pct: 60,
  discount_rate_annual_pct: 12,
  horizon_months: 24,
  growth_rate_monthly_pct: 2,

  requested_loan_amount: 30_000,
  loan_term_months: 36,
  interest_rate_annual_pct: 18,
  existing_debt_monthly: 0,
};

export const REGION_MAP: Record<string, Partial<BusinessProfile>> = {
  'tashkent-01':  { region_label: 'Toshkent — Yunusobod', population: 320_000, avg_income: 720, lat: 41.3611, lon: 69.2867 },
  'samarkand-01': { region_label: 'Samarqand — Markaz',   population: 530_000, avg_income: 480, lat: 39.6542, lon: 66.9597 },
  'bukhara-01':   { region_label: 'Buxoro — Markaz',      population: 280_000, avg_income: 460, lat: 39.7747, lon: 64.4286 },
  'fergana-01':   { region_label: 'Fargʻona — Markaz',    population: 320_000, avg_income: 440, lat: 40.3894, lon: 71.7843 },
  'andijan-01':   { region_label: 'Andijon — Markaz',     population: 410_000, avg_income: 450, lat: 40.7821, lon: 72.3442 },
  'namangan-01':  { region_label: 'Namangan — Markaz',    population: 470_000, avg_income: 430, lat: 40.9983, lon: 71.6726 },
  'jizzakh-01':   { region_label: 'Jizzax',               population: 180_000, avg_income: 410, lat: 40.1158, lon: 67.8422 },
  'gulistan-01':  { region_label: 'Guliston — Markaz',    population: 190_000, avg_income: 420, lat: 40.4897, lon: 68.7842 },
  'navoiy-01':    { region_label: 'Navoiy — Markaz',      population: 160_000, avg_income: 520, lat: 40.0844, lon: 65.3792 },
  'nukus-01':     { region_label: 'Nukus — Markaz',       population: 330_000, avg_income: 410, lat: 42.4619, lon: 59.6166 },
  'termez-01':    { region_label: 'Termiz — Markaz',      population: 190_000, avg_income: 400, lat: 37.2242, lon: 67.2783 },
};

export const MCC_MAP: Record<string, Partial<BusinessProfile>> = {
  '5812': { mcc_label: 'Restoran / Ovqatlanish',  niche: 'food',       avg_transaction_value: 15, monthly_transactions: 1_000, gross_margin_pct: 60 },
  '5814': { mcc_label: 'Tez ovqatlanish',         niche: 'food',       avg_transaction_value: 8,  monthly_transactions: 2_400, gross_margin_pct: 55 },
  '5411': { mcc_label: 'Oziq-ovqat doʻkoni',      niche: 'grocery',    avg_transaction_value: 22, monthly_transactions: 1_400, gross_margin_pct: 28 },
  '5651': { mcc_label: 'Oilaviy kiyim doʻkoni',   niche: 'apparel',    avg_transaction_value: 38, monthly_transactions: 420,   gross_margin_pct: 52 },
  '5621': { mcc_label: 'Ayollar kiyim doʻkoni',   niche: 'womens_clothing', avg_transaction_value: 42, monthly_transactions: 360, gross_margin_pct: 54 },
  '5712': { mcc_label: 'Mebel doʻkoni',           niche: 'furniture',  avg_transaction_value: 320,monthly_transactions: 80,    gross_margin_pct: 42 },
  '7011': { mcc_label: 'Mehmonxona',              niche: 'hotel',      avg_transaction_value: 95, monthly_transactions: 220,   gross_margin_pct: 65 },
  '7230': { mcc_label: 'Goʻzallik saloni',        niche: 'beauty',     avg_transaction_value: 18, monthly_transactions: 540,   gross_margin_pct: 70 },
  '7999': { mcc_label: 'Dam olish xizmatlari',    niche: 'recreation', avg_transaction_value: 25, monthly_transactions: 600,   gross_margin_pct: 60 },
  '5999': { mcc_label: 'Maxsus chakana savdo',    niche: 'retail',     avg_transaction_value: 28, monthly_transactions: 480,   gross_margin_pct: 48 },
  '8011': { mcc_label: 'Tibbiy xizmatlar',        niche: 'medical',    avg_transaction_value: 65, monthly_transactions: 240,   gross_margin_pct: 55 },
  '7542': { mcc_label: 'Avtomobil yuvish',        niche: 'recreation', avg_transaction_value: 6,  monthly_transactions: 2_500, gross_margin_pct: 65 },
  '5912': { mcc_label: 'Dorixona',                niche: 'pharmacy',   avg_transaction_value: 18, monthly_transactions: 1_200, gross_margin_pct: 35 },
  '5734': { mcc_label: 'Elektronika',             niche: 'electronics',avg_transaction_value: 220,monthly_transactions: 130,   gross_margin_pct: 28 },
  '5511': { mcc_label: 'Avtomobil savdosi',       niche: 'auto_dealer',avg_transaction_value: 6500,monthly_transactions: 12,   gross_margin_pct: 18 },
  '7372': { mcc_label: 'Dasturiy taʻminot',       niche: 'software',   avg_transaction_value: 280,monthly_transactions: 90,    gross_margin_pct: 78 },
  '5940': { mcc_label: 'Velosiped / Sport',       niche: 'sports',     avg_transaction_value: 95, monthly_transactions: 180,   gross_margin_pct: 38 },
  '5047': { mcc_label: 'Tibbiyot jihozlari',      niche: 'medical_equipment',avg_transaction_value: 320,monthly_transactions: 110,   gross_margin_pct: 30 },
};

export function profileFromContext(ctx: { region_id?: string; mcc_code?: string; monthly_revenue?: number; initial_investment?: number; }): BusinessProfile {
  const r = ctx.region_id ? REGION_MAP[ctx.region_id] ?? {} : {};
  const m = ctx.mcc_code ? MCC_MAP[ctx.mcc_code] ?? {} : {};
  return {
    ...DEFAULT_PROFILE,
    ...(ctx.region_id ? { region_id: ctx.region_id } : {}),
    ...r,
    ...(ctx.mcc_code ? { mcc_code: ctx.mcc_code } : {}),
    ...m,
    ...(ctx.monthly_revenue ? { monthly_revenue_estimate: ctx.monthly_revenue } : {}),
    ...(ctx.initial_investment ? { initial_investment: ctx.initial_investment } : {}),
  };
}

// ── Shared profile store ────────────────────────────────────────────────
// Single source of truth for the active business profile. Decoupled from
// sources/CSV uploads — this is what the chat sends and the LLM patches.
//
// Implemented as a module-level singleton + useSyncExternalStore so every
// component that calls useProfile() observes the same state and re-renders
// when any other component (or the LLM stream) updates it.
import { useCallback, useSyncExternalStore } from 'react';

// v2 bump — defaults changed from preset Tashkent/restaurant to empty so the
// LLM must ask the user for region/MCC/revenue/investment instead of running
// against stale saved values from older sessions.
const PROFILE_KEY = 'biziq_profile_v2';

function loadInitial(): BusinessProfile {
  if (typeof window === 'undefined') return DEFAULT_PROFILE;
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    if (!raw) return DEFAULT_PROFILE;
    const parsed = JSON.parse(raw) as Partial<BusinessProfile>;
    return { ...DEFAULT_PROFILE, ...parsed };
  } catch {
    return DEFAULT_PROFILE;
  }
}

let _profile: BusinessProfile = DEFAULT_PROFILE;
let _initialized = false;
const _listeners = new Set<() => void>();

function ensureInit() {
  if (_initialized || typeof window === 'undefined') return;
  _profile = loadInitial();
  _initialized = true;
}

function setProfile(next: BusinessProfile) {
  _profile = next;
  if (typeof window !== 'undefined') {
    try { localStorage.setItem(PROFILE_KEY, JSON.stringify(next)); } catch { /* ignore */ }
  }
  _listeners.forEach((fn) => fn());
}

function subscribe(fn: () => void): () => void {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}

function getSnapshot(): BusinessProfile {
  ensureInit();
  return _profile;
}

/** Read the current profile outside React render — useful inside long-lived
 *  closures (e.g. the SSE stream handler in NotebookLayout) that need the
 *  latest profile after an LLM-driven `update_profile` patch. */
export function getProfileSnapshot(): BusinessProfile {
  ensureInit();
  return _profile;
}

function getServerSnapshot(): BusinessProfile {
  return DEFAULT_PROFILE;
}

export function useProfile(): {
  profile: BusinessProfile;
  updateProfile: (patch: Partial<BusinessProfile>) => void;
  resetProfile: () => void;
} {
  const profile = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const updateProfile = useCallback((patch: Partial<BusinessProfile>) => {
    // Auto-derive region/MCC labels and dependent fields from the maps,
    // so passing only `region_id` produces a coherent profile (label, lat/lon,
    // population, etc. all in sync).
    const next: BusinessProfile = { ..._profile, ...patch };
    if (patch.region_id && REGION_MAP[patch.region_id]) {
      Object.assign(next, REGION_MAP[patch.region_id]);
      next.region_id = patch.region_id;
    }
    if (patch.mcc_code && MCC_MAP[patch.mcc_code]) {
      Object.assign(next, MCC_MAP[patch.mcc_code]);
      next.mcc_code = patch.mcc_code;
    }
    // Caller-supplied fields always win over auto-derived ones.
    Object.assign(next, patch);
    setProfile(next);
  }, []);

  const resetProfile = useCallback(() => setProfile(DEFAULT_PROFILE), []);

  return { profile, updateProfile, resetProfile };
}
