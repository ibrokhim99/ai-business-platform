import type { BusinessProfile } from './profile';
import type { ModelResult } from './runner';
import { clamp } from './format';

// ── Constants ──────────────────────────────────────────────────────────
const TARGET_COVERAGE    = 1.5;
const TERM_LADDER        = [12, 18, 24, 30, 36];
const COLLATERAL_HAIRCUT = 0.70;
const LGD_FLOOR          = 0.10;
const LGD_CAP            = 0.85;
const MIN_USEFUL_LOAN    = 5_000;

export const REQUIRED_MODEL_IDS = ['M-F1', 'M-F2', 'M-F3', 'M-D1', 'M-D3', 'M-D5'] as const;

// ── Types ──────────────────────────────────────────────────────────────
export type Verdict = 'APPROVE' | 'RIGHT-SIZE' | 'RESTRUCTURE' | 'DECLINE';
export type Binding = 'policy' | 'affordability' | 'requested';

export interface Scenario {
  loan: number;
  termMonths: number;
  monthlyPayment: number;
  totalInterest: number;
  coverage: number;
  pd: number;
  /** Expected total cost = principal + interest. */
  totalRepayment: number;
}

export interface BankRisk {
  lgd: number;
  ead: number;
  expectedLoss: number;
  collateralCoverage: number;
  unsecured: boolean;
}

export interface BorrowerRisk {
  pd: number;
  coverage: number;
  breakevenMonth: number;
  paybackMonths: number;
  monthsAheadOfBreakeven: number;
}

export interface RepaymentOverlayPoint {
  month: string;
  cashflow: number;          // cumulative business cash flow (from M-D5)
  repaid: number;            // cumulative loan repayment
}

export interface StressTest {
  revenueDropPct: number;
  stressCoverage: number;
  marginal: boolean;
}

export interface Recommendation {
  ready: true;
  verdict: Verdict;
  binding: Binding;
  requested: Scenario;
  recommended: Scenario;
  borrowerRisk: BorrowerRisk;
  bankRisk: BankRisk;
  overlay: RepaymentOverlayPoint[];
  loanRepaidMonth: number;
  stress: StressTest;
  narrative: string;
  policyMaxLoan: number;
  affordableLoan: number;
}

export interface RecommendationSkeleton {
  ready: false;
  readyCount: number;
  totalRequired: number;
  missing: string[];
  errored: string[];
  /** True after the LLM stream has emitted `done` — UI uses this to flip from
   *  "preparing…" to "not applicable" once we know the missing models will
   *  never run (LLM didn't pick them). */
  streamDone?: boolean;
}

export type RecommendationCard = Recommendation | RecommendationSkeleton;

// ── Helpers ────────────────────────────────────────────────────────────
function paymentFor(loan: number, termMonths: number, annualRatePct: number): number {
  const r = annualRatePct / 1200;
  if (r === 0) return loan / termMonths;
  return (loan * r) / (1 - Math.pow(1 + r, -termMonths));
}

function affordableFor(payment: number, termMonths: number, annualRatePct: number): number {
  const r = annualRatePct / 1200;
  if (r === 0) return payment * termMonths;
  return (payment * (1 - Math.pow(1 + r, -termMonths))) / r;
}

function readyState(results: ModelResult[]): RecommendationSkeleton {
  const missing: string[] = [];
  const errored: string[] = [];
  let readyCount = 0;
  for (const id of REQUIRED_MODEL_IDS) {
    const r = results.find((x) => x.modelId === id);
    if (!r) { missing.push(id); continue; }
    if (r.status === 'done') readyCount++;
    else if (r.status === 'error') errored.push(id);
    else missing.push(id);
  }
  return {
    ready: false,
    readyCount,
    totalRequired: REQUIRED_MODEL_IDS.length,
    missing,
    errored,
  };
}

function pickBinding(candidates: { policy: number; affordability: number; requested: number }): { value: number; binding: Binding } {
  let value = candidates.requested;
  let binding: Binding = 'requested';
  if (candidates.affordability < value) { value = candidates.affordability; binding = 'affordability'; }
  if (candidates.policy < value) { value = candidates.policy; binding = 'policy'; }
  return { value, binding };
}

// ── Main entry ─────────────────────────────────────────────────────────
export function buildRecommendation(
  profile: BusinessProfile,
  results: ModelResult[],
  streamDone = false,
): RecommendationCard {
  // Gate
  const skel = readyState(results);
  if (skel.readyCount < REQUIRED_MODEL_IDS.length) return { ...skel, streamDone };

  const get = (id: string): Record<string, unknown> | undefined =>
    results.find((r) => r.modelId === id)?.prediction;

  const f1 = get('M-F1') ?? {};
  const f2 = get('M-F2') ?? {};
  // const f3 = get('M-F3') ?? {}; // dti_ratio at requested — informative, not required for synthesis math
  const d1 = get('M-D1') ?? {};
  const d3 = get('M-D3') ?? {};
  const d5 = get('M-D5') ?? {};

  // Backend uses default_probability / recommended_loan / monthly_cashflows[].cumulative
  // / break_even_month; older fallbacks use shorter names.
  const pdAtRequested  = Number(f1.default_probability ?? f1.pd ?? 0.2);
  const policyMaxLoan  = Math.max(0, Number(
    f2.recommended_loan ?? f2.max_loan ?? f1.max_recommended_loan ?? 0,
  ));
  const cashflows      = Array.isArray(d5.monthly_cashflows)
    ? (d5.monthly_cashflows as Array<{ cumulative?: number; net_cashflow?: number }>)
    : [];
  const cumulCF        = cashflows.length
    ? cashflows.map((c) => Number(c.cumulative ?? 0))
    : (Array.isArray(d5.cumulative_cashflow) ? (d5.cumulative_cashflow as number[]).map(Number) : []);
  const breakevenMonth = Math.max(1, Number(d5.break_even_month ?? d5.breakeven_month ?? 18));
  const paybackMonths  = Number(d3.payback_months ?? 24);
  // Derive monthly net cashflow: prefer D1 if present, else average D5's net_cashflow,
  // else fall back to a profile-based estimate.
  const avgNetFromD5   = cashflows.length
    ? cashflows.reduce((s, c) => s + Number(c.net_cashflow ?? 0), 0) / cashflows.length
    : 0;
  const monthlyNetCF   = Number(
    d1.monthly_net_cashflow
    ?? (avgNetFromD5 || (profile.monthly_revenue_estimate - profile.monthly_fixed_costs - profile.monthly_rent)),
  );

  const requestedLoan = profile.requested_loan_amount;
  const requestedTerm = profile.loan_term_months;
  const ratePct       = profile.interest_rate_annual_pct;

  // Step 1 — Hard short-circuits
  if (requestedLoan <= 0) {
    return {
      ready: true,
      verdict: 'APPROVE',
      binding: 'requested',
      requested: zeroScenario(),
      recommended: zeroScenario(),
      borrowerRisk: { pd: 0, coverage: Infinity, breakevenMonth, paybackMonths: 0, monthsAheadOfBreakeven: 0 },
      bankRisk: { lgd: 0, ead: 0, expectedLoss: 0, collateralCoverage: 0, unsecured: true },
      overlay: [],
      loanRepaidMonth: 0,
      stress: { revenueDropPct: 20, stressCoverage: Infinity, marginal: false },
      narrative: 'Kredit soʻralmagan — tavsiya kerak emas.',
      policyMaxLoan,
      affordableLoan: 0,
    };
  }

  if (monthlyNetCF <= 0) {
    const requested = scenarioFor(requestedLoan, requestedTerm, ratePct, monthlyNetCF, pdAtRequested);
    return {
      ready: true,
      verdict: 'DECLINE',
      binding: 'affordability',
      requested,
      recommended: { ...requested, loan: 0, monthlyPayment: 0, totalInterest: 0, totalRepayment: 0, coverage: 0, pd: pdAtRequested },
      borrowerRisk: { pd: pdAtRequested, coverage: 0, breakevenMonth, paybackMonths, monthsAheadOfBreakeven: -paybackMonths },
      bankRisk: bankRiskFor(0, profile.collateral_value, requestedTerm, pdAtRequested),
      overlay: [],
      loanRepaidMonth: 0,
      stress: { revenueDropPct: 20, stressCoverage: 0, marginal: true },
      narrative: 'Manfiy pul oqimi — biznes hozircha hech qanday kreditni qoplay olmaydi. Avval operatsiyalarni tiklang.',
      policyMaxLoan,
      affordableLoan: 0,
    };
  }

  // Step 2 — Affordability ceiling
  const safePayment = Math.min(monthlyNetCF * 0.55, profile.monthly_revenue_estimate * 0.20);

  // Step 3 — Term scan: shortest term that hits target coverage
  let chosenTerm = requestedTerm;
  let affordableLoan = affordableFor(safePayment, chosenTerm, ratePct);
  let targetTermFound = false;
  for (const n of TERM_LADDER) {
    const aff = affordableFor(safePayment, n, ratePct);
    const trialLoan = Math.min(aff, requestedLoan, policyMaxLoan);
    if (trialLoan < MIN_USEFUL_LOAN) continue;
    const pay = paymentFor(trialLoan, n, ratePct);
    const cov = monthlyNetCF / pay;
    if (cov >= TARGET_COVERAGE) {
      chosenTerm = n;
      affordableLoan = aff;
      targetTermFound = true;
      break;
    }
  }
  if (!targetTermFound) {
    affordableLoan = affordableFor(safePayment, chosenTerm, ratePct);
  }

  // Step 4 — Recommended loan + binding constraint
  const candidates = {
    policy: policyMaxLoan,
    affordability: affordableLoan,
    requested: requestedLoan,
  };
  const { value: recommendedLoan, binding } = pickBinding(candidates);

  // Step 5 — Per-scenario amortization
  const requestedScn = scenarioFor(requestedLoan, requestedTerm, ratePct, monthlyNetCF, pdAtRequested);

  // Step 6 — Coverage-anchored PD adjustment
  const recommendedPaymentRaw = paymentFor(Math.max(MIN_USEFUL_LOAN, recommendedLoan), chosenTerm, ratePct);
  const coverageRecommendedRaw = monthlyNetCF / recommendedPaymentRaw;
  const pdAdj = pdAtRequested * clamp(requestedScn.coverage / coverageRecommendedRaw, 0.4, 1.0);

  const recommendedScn = scenarioFor(recommendedLoan, chosenTerm, ratePct, monthlyNetCF, pdAdj);

  // Step 7 — Bank-side risk on recommended scenario
  const bankRisk = bankRiskFor(recommendedLoan, profile.collateral_value, chosenTerm, pdAdj);

  // Step 8 — Repayment overlay (consume D5 series, do not re-extrapolate)
  const overlay = buildOverlay(cumulCF, recommendedScn);
  const loanRepaidMonth = chosenTerm;

  // Step 9 — Stress test
  const cogsRate = clamp(profile.cogs_pct / 100, 0, 1);
  const revenueDelta = profile.monthly_revenue_estimate * 0.20;
  const stressNetCF = monthlyNetCF - revenueDelta * (1 - cogsRate);
  const stressCoverage = recommendedScn.monthlyPayment > 0 ? stressNetCF / recommendedScn.monthlyPayment : 0;
  const stress: StressTest = {
    revenueDropPct: 20,
    stressCoverage,
    marginal: stressCoverage < 1.2,
  };

  // Step 10 — Verdict ladder (most-restrictive-first)
  const verdict = computeVerdict({
    pd: pdAdj,
    coverage: recommendedScn.coverage,
    recommended: recommendedLoan,
    requested: requestedLoan,
    targetTermFound,
  });

  // Step 11 — Headline narrative + months ahead
  const monthsAheadOfBreakeven = breakevenMonth - paybackMonths;
  const borrowerRisk: BorrowerRisk = {
    pd: pdAdj,
    coverage: recommendedScn.coverage,
    breakevenMonth,
    paybackMonths,
    monthsAheadOfBreakeven,
  };
  const narrative = buildNarrative({
    verdict, binding, requestedScn, recommendedScn, monthsAheadOfBreakeven, profile,
  });

  return {
    ready: true,
    verdict,
    binding,
    requested: requestedScn,
    recommended: recommendedScn,
    borrowerRisk,
    bankRisk,
    overlay,
    loanRepaidMonth,
    stress,
    narrative,
    policyMaxLoan,
    affordableLoan,
  };
}

// ── Sub-helpers ────────────────────────────────────────────────────────
function zeroScenario(): Scenario {
  return { loan: 0, termMonths: 0, monthlyPayment: 0, totalInterest: 0, coverage: 0, pd: 0, totalRepayment: 0 };
}

function scenarioFor(loan: number, termMonths: number, annualRatePct: number, monthlyNetCF: number, pd: number): Scenario {
  if (loan <= 0 || termMonths <= 0) return { ...zeroScenario(), pd };
  const monthlyPayment = paymentFor(loan, termMonths, annualRatePct);
  const totalRepayment = monthlyPayment * termMonths;
  const totalInterest = totalRepayment - loan;
  const coverage = monthlyPayment > 0 ? monthlyNetCF / monthlyPayment : Infinity;
  return { loan, termMonths, monthlyPayment, totalInterest, totalRepayment, coverage, pd };
}

function bankRiskFor(loan: number, collateralValue: number, termMonths: number, pd: number): BankRisk {
  if (loan <= 0) return { lgd: 0, ead: 0, expectedLoss: 0, collateralCoverage: 0, unsecured: collateralValue <= 0 };
  const effectiveCollateral = collateralValue * COLLATERAL_HAIRCUT;
  const lgd = clamp(1 - effectiveCollateral / loan, LGD_FLOOR, LGD_CAP);
  // Mid-life balance: average outstanding over the life of the loan
  const ead = loan * (termMonths + 1) / (2 * termMonths);
  const expectedLoss = pd * lgd * ead;
  return {
    lgd,
    ead,
    expectedLoss,
    collateralCoverage: effectiveCollateral / loan,
    unsecured: collateralValue <= 0,
  };
}

function buildOverlay(cumulCF: number[], rec: Scenario): RepaymentOverlayPoint[] {
  if (cumulCF.length === 0) return [];
  const horizon = cumulCF.length;
  const result: RepaymentOverlayPoint[] = [];
  for (let i = 0; i < horizon; i++) {
    const month = i + 1;
    const repaid = Math.min(rec.loan, rec.monthlyPayment * month);
    result.push({ month: `M${month}`, cashflow: cumulCF[i], repaid });
  }
  return result;
}

function computeVerdict(args: {
  pd: number; coverage: number; recommended: number; requested: number; targetTermFound: boolean;
}): Verdict {
  const { pd, coverage, recommended, requested, targetTermFound } = args;
  if (pd >= 0.30 || coverage < 1.0 || recommended < MIN_USEFUL_LOAN) return 'DECLINE';
  if (pd >= 0.18 || coverage < 1.3 || !targetTermFound) return 'RESTRUCTURE';
  if (recommended < 0.85 * requested) return 'RIGHT-SIZE';
  return 'APPROVE';
}

function buildNarrative(args: {
  verdict: Verdict;
  binding: Binding;
  requestedScn: Scenario;
  recommendedScn: Scenario;
  monthsAheadOfBreakeven: number;
  profile: BusinessProfile;
}): string {
  const { verdict, binding, requestedScn, recommendedScn, monthsAheadOfBreakeven } = args;
  const moneyShort = (n: number) => {
    if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
    if (n >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
    return `$${Math.round(n)}`;
  };
  const termText = (n: number) => {
    if (n === 12) return '12 oy (1 yil)';
    if (n === 24) return '24 oy (2 yil)';
    if (n === 36) return '36 oy (3 yil)';
    return `${n} oy`;
  };
  const bindingLabel: Record<Binding, string> = {
    requested:     'sizning soʻrovingiz',
    affordability: 'naqd pul oqimi imkoniyati',
    policy:        'bank siyosati chegarasi',
  };
  const ahead = monthsAheadOfBreakeven > 0
    ? `tenglik nuqtasidan **${monthsAheadOfBreakeven} oy oldin** qaytariladi`
    : monthsAheadOfBreakeven < 0
      ? `tenglik nuqtasidan **${Math.abs(monthsAheadOfBreakeven)} oy keyin** qaytariladi — xavfli oraliq`
      : 'tenglik nuqtasi bilan bir vaqtda qaytariladi';

  if (verdict === 'DECLINE') {
    return `Soʻralgan **${moneyShort(requestedScn.loan)}** uchun rad etiladi — qoplash **${recommendedScn.coverage.toFixed(2)}×** va sozlangan defolt riski juda yuqori. Shartlarni qayta tuzing yoki avval daromadni oshiring.`;
  }
  if (verdict === 'RESTRUCTURE') {
    return `Qayta tuzish tavsiya etiladi: **${moneyShort(recommendedScn.loan)}** ni **${termText(recommendedScn.termMonths)}** muddatga oling, oylik toʻlov **${moneyShort(recommendedScn.monthlyPayment)}**. Qoplash **${recommendedScn.coverage.toFixed(2)}×** — ishlaydi, lekin tor; qoʻshimcha garov bering yoki muddatni qisqartiring.`;
  }
  if (verdict === 'RIGHT-SIZE') {
    return `Hajmni **${moneyShort(requestedScn.loan)}** dan **${moneyShort(recommendedScn.loan)}** ga moslang, **${termText(recommendedScn.termMonths)}** muddatga, oylik toʻlov **${moneyShort(recommendedScn.monthlyPayment)}** — ${bindingLabel[binding]} bilan cheklangan. Qoplash **${recommendedScn.coverage.toFixed(2)}×**, ${ahead}.`;
  }
  // APPROVE
  return `**${moneyShort(recommendedScn.loan)}** ni **${termText(recommendedScn.termMonths)}** muddatga oylik **${moneyShort(recommendedScn.monthlyPayment)}** toʻlov bilan tasdiqlash mumkin — qoplash **${recommendedScn.coverage.toFixed(2)}×**, ${ahead}.`;
}
