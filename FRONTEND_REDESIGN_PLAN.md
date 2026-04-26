# Frontend Redesign — Unified Intake → Dynamic Results Dashboard

## Goal
User fills **one** business-intake form → frontend fans out to all 39 ML endpoints → results render as a **single multi-section dashboard** with the right chart per model (bar, line, gauge, radar, donut, heatmap, KPI cards, etc.).

---

## 1. UX Flow

```
/onboarding           ──▶  /analyze (running…)  ──▶  /results
   intake wizard           progress per model        dashboard with charts
   (4 steps)               (real-time tile fills)    (7 collapsible sections)
```

- Existing `/dashboard/block-*` pages stay as **deep-dive / manual** mode
- New flow becomes the **default landing** after login

---

## 2. Single Intake Form (Wizard, 4 steps)

One form, ~25 fields, mostly with sensible defaults. Required fields are **bold**.

### Step 1 — Business Basics
- **Niche / MCC code** (searchable dropdown: 5812 Food, 5411 Grocery, 5651 Apparel, 7011 Hotel…)
- **Region** (dropdown of seeded regions)
- **Initial investment** ($)
- Business age (months) — default `0` if new
- Owner experience years — default `0`
- Owner credit history score (300–850) — default `680`
- Collateral value ($) — default `0`

### Step 2 — Location
- **Latitude / Longitude** (with map picker)
- **Radius (m)** — default `500`
- Facade direction (degrees 0–360) — default `180`
- Walking minutes for isochrone — default `10`

### Step 3 — Financials
- **Monthly revenue estimate** ($)
- **Monthly fixed costs** ($)
- **Monthly rent** ($)
- COGS % of revenue — default `40`
- Avg transaction value ($) — default `15`
- Monthly transactions — default computed from revenue/avg_txn
- CAC ($) — default `5`
- Monthly churn % — default `5`
- Gross margin % — default `60`
- Discount rate (annual %) — default `12`
- Horizon (months) — default `24`
- Growth rate (monthly %) — default `2`

### Step 4 — Credit (only if seeking financing)
- Requested loan amount ($)
- Loan term (months) — default `36`
- Interest rate (annual %) — default `18`
- Existing debt monthly ($) — default `0`

A small **"Use defaults"** button on each step pre-fills typical values for the chosen MCC + region (looked up from `data/test/block_*.csv` later — for v1 we hard-code defaults).

---

## 3. Orchestrator (client-side fan-out, v1)

`src/lib/orchestrator.ts` exposes:

```ts
runAllModels(intake: IntakeForm) :
  AsyncGenerator<{ modelId: string; status: 'pending'|'running'|'done'|'error'; data?: unknown; error?: string; latencyMs?: number }>
```

Implementation:
- Maps the intake DTO → 39 per-model input shapes (one mapper per model)
- Fires all 39 `predict()` calls via `Promise.allSettled`
- Yields status updates as each settles → UI tiles fill in

Why client-side?
- Zero backend changes
- Streams results to the UI as they arrive (better perceived perf)
- Failures isolated per model

(Backend orchestrator endpoint `POST /api/v1/predict/all` is a v2 optimization.)

---

## 4. Results Dashboard — Component Per Model

Single registry: `src/components/results/registry.ts`

```ts
type Renderer = (prediction: unknown) => JSX.Element
const RENDERERS: Record<string, Renderer> = {
  'M-A1': MarketSizingChart,
  'M-A2': GapAnalysisChart,
  ...
}
```

### Chart-type assignments

| Block | Model | Chart |
|-------|-------|-------|
| **A** | M-A1 Market Sizing | Stacked bar TAM/SAM/SOM + CI error bars |
| | M-A2 GAP Analysis | Side-by-side bar (normative vs actual) + gap badge |
| | M-A3 Saturation | Radial gauge 0–100 with status pill |
| | M-A4 Wallet Share | Donut (your share / competitors) |
| | M-A5 Niche Opportunity | Score gauge + radar of sub-factors |
| | M-A6 Cross-Niche | Horizontal bar of synergy per adjacent MCC |
| **B** | M-B1 Demand Forecast | Line chart 12/24/36 mo + confidence band |
| | M-B2 Seasonality | Monthly bar chart with peak/trough highlights |
| | M-B3 Population Dynamics | Line chart projection |
| | M-B4 Income Trend | Line chart |
| | M-B5 MCC Trend | Line + changepoint markers |
| | M-B6 Business Reg Forecast | Stacked area (existing + new) |
| **C** | M-C1 Location Score | Radar of 8 sub-factors + grade pill |
| | M-C2 Traffic Scoring | Hourly bar / line chart, peak hours highlighted |
| | M-C3 Isochrone Demand | Concentric donut (5/10 min reach) |
| | M-C4 Street Vitality | Gauge + KPI cards |
| | M-C5 Anchor Effect | Horizontal bar of anchors + halo number |
| | M-C6 Visibility | Compass diagram + score |
| **D** | M-D1 Viability | Survival probability gauge + verdict banner |
| | M-D2 Unit Economics | KPI cards (LTV, CAC, payback) + ratio bar |
| | M-D3 ROI | KPI cards (NPV, IRR, payback) |
| | M-D4 Rental Burden | Threshold bar (safe/warn/critical) |
| | M-D5 Cash Flow Sim | Area chart 24 months (revenue / costs / cumulative) |
| | M-D6 COGS & Margin | Donut + benchmark gap |
| **E** | M-E1 Competitor Intel | Table + competitive intensity badge |
| | M-E2 Churn | Probability gauge |
| | M-E3 Regulatory Risk | Stacked bar of categories |
| | M-E4 Entry Barrier | Gauge + barrier list |
| | M-E5 Price Pressure | Number line: your price vs market band |
| **F** | M-F1 Credit Risk | Big score card + grade + decision banner |
| | M-F2 Loan Sizing | Bar (requested vs recommended max) |
| | M-F3 DTI Predictor | Line chart (6/12/24 mo) |
| | M-F4 NPL Warning | Probability gauge + alert badges |
| | M-F5 Product Recommender | Card list (priority-sorted) |
| **G** | M-G1 Customer Profiler | Donut of segments + age/income table |
| | M-G2 Day Population | Stacked bar (residents/workers/visitors) |
| | M-G3 Behavior | Stacked horizontal bar |
| | M-G4 Brand Affinity | Horizontal bar of top brands |
| | M-G5 Spending Power | Gauge + category donut |

### Reusable primitives
- `<Gauge value=... max=100 />` (radial)
- `<KpiCard label value unit trend />`
- `<MetricBar value benchmark thresholds />`
- `<TimeSeries data xKey yKey ciLower ciUpper />`
- `<DonutChart slices />`
- `<RadarChart axes values />`
- `<HeatmapChart rows cols values />`
- `<StatusPill text variant />`

---

## 5. Page Structure

```
/results
├── Header              (business name, location pin, summary score)
├── ExecutiveSummary    (top-level score: viability + credit + opportunity)
├── Block A section     (collapsed/expanded, 6 model cards in grid)
├── Block B section
├── Block C section
├── Block D section
├── Block E section     (gated)
├── Block F section     (gated)
├── Block G section
└── Footer              (export PDF button — v2)
```

- Each section: title + run-time totals (e.g. "Block A — 6/6 done in 0.4s")
- Each card: title, chart, key insight (1-line takeaway), latency, retry button on error

---

## 6. Tech Choices

- **Recharts** — primary chart lib (bar/line/area/radar/donut/scatter, Next.js-friendly, no D3 setup)
- **react-hook-form + zod** — form validation in the wizard
- **Existing Tailwind / dark fintech theme** — keep look and feel
- No new backend changes for v1
- Map picker for lat/lon: `react-leaflet` (optional, can use plain inputs first)

New dependencies:
```
recharts react-hook-form zod @hookform/resolvers
```

---

## 7. File Plan

```
frontend/src/
├── app/
│   ├── onboarding/
│   │   └── page.tsx              ← new — 4-step wizard
│   ├── results/
│   │   └── page.tsx              ← new — orchestrator + dashboard
│   └── dashboard/                ← keep, becomes "advanced/manual mode"
├── components/
│   ├── intake/
│   │   ├── IntakeWizard.tsx
│   │   ├── Step1Business.tsx
│   │   ├── Step2Location.tsx
│   │   ├── Step3Financials.tsx
│   │   └── Step4Credit.tsx
│   ├── results/
│   │   ├── registry.ts
│   │   ├── ResultCard.tsx
│   │   ├── BlockSection.tsx
│   │   ├── ExecutiveSummary.tsx
│   │   ├── primitives/
│   │   │   ├── Gauge.tsx
│   │   │   ├── KpiCard.tsx
│   │   │   ├── MetricBar.tsx
│   │   │   ├── TimeSeries.tsx
│   │   │   ├── DonutChart.tsx
│   │   │   ├── RadarChart.tsx
│   │   │   ├── HeatmapChart.tsx
│   │   │   └── StatusPill.tsx
│   │   └── models/
│   │       ├── M-A1-MarketSizing.tsx
│   │       ├── M-A2-GapAnalysis.tsx
│   │       └── ... (35 more — one per model)
├── lib/
│   ├── intake-mappers.ts         ← intake DTO → 39 per-model inputs
│   ├── orchestrator.ts           ← Promise.allSettled fan-out
│   └── api.ts                    ← existing
└── types/
    ├── intake.ts                 ← unified intake DTO
    └── index.ts                  ← existing
```

---

## 8. Implementation Phases

| Phase | Scope | Estimate |
|-------|-------|----------|
| **P1 — Scaffold** | install Recharts, create types, intake wizard skeleton, orchestrator with mock data | 1 session |
| **P2 — Mappers** | unified IntakeForm → 39 per-model input mappers; verify each endpoint accepts | 1 session |
| **P3 — Primitives** | Gauge, KpiCard, TimeSeries, Donut, Radar, Heatmap, StatusPill | 1 session |
| **P4 — Block A+B+C** | 18 model cards with their assigned charts | 1–2 sessions |
| **P5 — Block D+E+F+G** | remaining 21 model cards | 1–2 sessions |
| **P6 — Polish** | executive summary, role gating, error/retry, mobile responsive | 1 session |

Implementation will start at **P1** if you say "go." Existing `/dashboard/block-*` pages remain untouched.

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| 39 simultaneous API calls overwhelm backend or rate-limit | Batch in groups of 8; fan out per block |
| Some models fail because intake field is missing | Mappers include defaults; failed cards show "Retry" without blocking page |
| Chart library bundle size | Recharts is tree-shakeable; only import used components |
| Role-gated blocks (E, F) | Hide sections + skip those endpoint calls based on JWT role |
| Data shape changes between backend and types | Add a runtime zod schema per model output; if validation fails, render fallback "raw JSON" view |

---

## 10. Open questions (default if unanswered)

1. **Map picker for lat/lon?** → Default: plain numeric inputs in v1; add `react-leaflet` later.
2. **PDF export of results?** → v2.
3. **Save / compare scenarios?** → v2 (would need a backend `scenarios` table).
4. **i18n (Uzbek / Russian)?** → English-only in v1; structured for i18n later.
