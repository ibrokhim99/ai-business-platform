# Miro Board — Problem / Solution Schema
## AI Business Intelligence Platform (39 models · 7 blocks)

A board-ready layout. Each section maps to a Miro **frame**; bullet items become **sticky notes**; arrows show problem → solution → outcome flow.

---

## Suggested Miro Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  FRAME 1 — CONTEXT                                                    │
│  Stakeholders · Goals · Pain points                                   │
└──────────────────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│  FRAME 2 — PROBLEMS       │──▶│  FRAME 3 — SOLUTIONS      │
│  (red/orange stickies)    │   │  (green/blue stickies)    │
│  Bank pains · SMB pains   │   │  39 ML models, 7 blocks   │
└──────────────────────────┘   └──────────────────────────┘
                                          │
                                          ▼
                                ┌──────────────────────────┐
                                │  FRAME 4 — OUTCOMES       │
                                │  KPIs · Metrics           │
                                └──────────────────────────┘
```

---

## FRAME 1 — Context

### Stakeholders (sticky color: gray)
- **Bank** — credit officers, analysts, product managers, risk team
- **SMB Customer** — entrepreneur opening or scaling a business
- **Bank Admin** — platform owner, sets policies and roles

### High-level goals (sticky color: yellow)
- Reduce NPL (non-performing loans)
- Increase credit approval throughput with confidence
- Help SMBs choose viable businesses + locations
- Personalize banking products (loans, leasing, guarantees)

---

## FRAME 2 — Problems  (red/orange sticky notes)

### Cluster 1 — Bank Risk & Credit
| ID | Problem | Impact |
|----|---------|--------|
| P-1 | Credit scoring uses generic models, ignores location × niche × customer | High NPL on SMB loans |
| P-2 | Defaults detected late (after missed payments) | Provisioning losses |
| P-3 | Loan size guessed manually, often mismatched to cash flow | Either over-leveraged borrower or under-served |
| P-4 | DTI not projected forward — only at origination | Hidden risk 6–24 months out |
| P-5 | Bank product recommendations are not personalized | Low cross-sell rate |

### Cluster 2 — Market Knowledge Gap
| ID | Problem | Impact |
|----|---------|--------|
| P-6 | No reliable estimate of TAM / SAM / SOM by niche × location | Poor go-to-market decisions |
| P-7 | Saturation and gap (normative vs actual) is unclear | Banks fund duplicate businesses |
| P-8 | No demand forecast — entrepreneurs guess | First-2-year closure rate is high |
| P-9 | Seasonality (Ramadan, Navruz, weddings) not modeled | Cash flow shocks |
| P-10 | New competitors (business registrations) unforeseen | Margins erode |

### Cluster 3 — Location & Footfall
| ID | Problem | Impact |
|----|---------|--------|
| P-11 | Location chosen by intuition, not data | Wrong rent, wrong traffic |
| P-12 | Pedestrian / vehicle traffic by hour unknown | Operating hours mis-set |
| P-13 | 5/10-min walking radius demand unmodeled | Bad catchment estimate |
| P-14 | Anchor effects (mall, mosque, market) ignored | Underestimated traffic |
| P-15 | Visibility from street unmeasured | Lost walk-ins |

### Cluster 4 — Financial Viability
| ID | Problem | Impact |
|----|---------|--------|
| P-16 | 2-year survival probability not computed | Banks lend to weak plans |
| P-17 | Unit economics (LTV, CAC, payback) absent | Burn rate hidden |
| P-18 | ROI / NPV not standardized | Inconsistent investment decisions |
| P-19 | Rent burden ratio not flagged | Top driver of failure |
| P-20 | No 24-month cash flow simulation | Cash gaps surprise the borrower |

### Cluster 5 — Competition & Behavior
| ID | Problem | Impact |
|----|---------|--------|
| P-21 | Competitor map is manual, outdated | Strategy lags |
| P-22 | Churn risk per niche/location not quantified | Bad lending segments |
| P-23 | Regulatory / inspection risk not scored | Compliance fines |
| P-24 | Price pressure and elasticity unknown | Margin loss |
| P-25 | Customer audience profile per location unclear | Wrong product mix |

---

## FRAME 3 — Solutions  (green/blue sticky notes)

Each solution is **one ML model**. Group by block frame.

### Block A — Market Analysis (solves P-6, P-7, P-10)
- **M-A1 Market Sizing** — TAM/SAM/SOM (Bayesian + bottom-up)
- **M-A2 GAP Analysis** — normative vs actual outlets
- **M-A3 Saturation Index** — 0–100 composite
- **M-A4 Wallet Share Estimator** — ensemble regression
- **M-A5 Niche Opportunity Score** — XGBoost + weighted scoring
- **M-A6 Cross-Niche Cannibalization** — MCC graph

### Block B — Forecasting (solves P-8, P-9, P-10)
- **M-B1 Demand Forecasting** — 12/24/36 mo (LSTM + Prophet)
- **M-B2 Seasonality** — Ramadan, Navruz, weddings (STL + Fourier)
- **M-B3 Population Dynamics** — cohort-component
- **M-B4 Income Trend** — ARIMA + macro factors
- **M-B5 MCC Trend Detector** — PELT changepoints
- **M-B6 Business Registration Forecast** — competitor inflow

### Block C — Location & Traffic (solves P-11, P-12, P-13, P-14, P-15)
- **M-C1 Location Score** — 8-factor weighted index
- **M-C2 Traffic Scoring** — gradient boosting + GPS
- **M-C3 Isochrone Demand** — 5/10-min OSM network
- **M-C4 Street Vitality Index** — POI + registrations
- **M-C5 Anchor Effect** — gravity model
- **M-C6 Visibility Score** — geometric

### Block D — Financial Viability (solves P-16, P-17, P-18, P-19, P-20)
- **M-D1 Viability Check** — 2-year survival (Monte Carlo)
- **M-D2 Unit Economics** — LTV / CAC / payback
- **M-D3 ROI Estimator** — DCF + NPV
- **M-D4 Rental Burden** — threshold model
- **M-D5 Cash Flow Simulator** — 24-mo Monte Carlo
- **M-D6 COGS & Margin** — sectoral benchmarks

### Block E — Competition & Risk (solves P-21, P-22, P-23, P-24)
- **M-E1 Competitor Intelligence** — spatial query + NLP
- **M-E2 Churn Prediction** — 50K SMB XGBoost
- **M-E3 Regulatory Risk Score** — rules + fines history
- **M-E4 Market Entry Barrier** — composite index
- **M-E5 Price Pressure** — hedonic + elasticity

### Block F — Credit & Banking (solves P-1, P-2, P-3, P-4, P-5)
- **M-F1 Credit Risk Score** — customer × location × niche (LightGBM)
- **M-F2 Loan Sizing Recommender** — cashflow regression
- **M-F3 DTI Predictor** — 6/12/24-mo projection
- **M-F4 NPL Early Warning** — IsolationForest + LSTM
- **M-F5 Bank Product Recommender** — collaborative filtering

### Block G — Social Profile (solves P-25)
- **M-G1 Customer Segment Profiler** — K-means / DBSCAN
- **M-G2 Day Population Estimator** — gravity + GPS
- **M-G3 Consumer Behavior Classifier** — MCC sequence NLP
- **M-G4 Brand Affinity** — collaborative filtering
- **M-G5 Spending Power Index** — spatial interpolation heatmap

---

## FRAME 4 — Outcomes / KPIs  (purple sticky notes)

| Outcome | Owner | Metric | Driven by |
|---------|-------|--------|-----------|
| Lower NPL rate | Bank Risk | NPL % ↓ 20–40% | F1, F4, E2 |
| Faster credit decisions | Credit Officers | TAT ↓ 50% | F1, F2, F3 |
| Higher cross-sell | Product Mgmt | Products/customer ↑ | F5, G1 |
| Better SMB survival | Customer | 2-yr survival ↑ | D1, D5, E2 |
| Better location ROI | Customer | ROI ↑, payback ↓ | C1–C6, D3 |
| Targeted go-to-market | Bank Strategy | Niche fit ↑ | A1–A6, B1 |

---

## Problem → Solution → Outcome Map  (arrows in Miro)

```
P-1 Credit scoring weak ───────────▶ M-F1 ─────────▶ NPL ↓
P-2 Late default detection ─────────▶ M-F4 ─────────▶ Provisioning ↓
P-3 Wrong loan size ───────────────▶ M-F2 ─────────▶ Healthier portfolio
P-4 DTI not projected ─────────────▶ M-F3 ─────────▶ 24-mo risk visible
P-5 Generic product offers ────────▶ M-F5 + M-G1 ──▶ Cross-sell ↑

P-6 No TAM/SAM/SOM ─────────────────▶ M-A1
P-7 Unknown saturation ─────────────▶ M-A2 + M-A3
P-8 Demand guessing ────────────────▶ M-B1 + M-B2 ──▶ 2-yr survival ↑
P-10 Competitor inflow ─────────────▶ M-B6 + M-E1

P-11..P-15 Location pain ───────────▶ M-C1..M-C6 ──▶ Location ROI ↑

P-16..P-20 Financial pain ──────────▶ M-D1..M-D6 ──▶ Viability ↑

P-21..P-24 Competition pain ────────▶ M-E1..M-E5
P-25 Audience pain ─────────────────▶ M-G1..M-G5
```

---

## Cross-cutting capabilities (system-level frame)

Place in a separate frame at the bottom — these enable every model:

- **Auth & RBAC** — JWT, 4 roles (admin / credit_officer / bank_analyst / customer)
- **Explainability** — `?explain=true` returns feature attributions per prediction
- **Model registry & versioning** — MLflow, retrain via Celery
- **Caching** — Redis per-block TTL (15 min for credit, 24 h for location)
- **Audit log** — every prediction stored in PostgreSQL
- **Metrics & tracing** — Prometheus + request-ID per call

---

## How to import into Miro

1. Create a new Miro board.
2. Add 4 large frames named: **Context**, **Problems**, **Solutions**, **Outcomes**.
3. For each cluster (P-1…P-25) drop a red sticky with the problem ID + one-line text.
4. For each model (M-A1…M-G5) drop a green sticky inside its block sub-frame.
5. Use Miro **connectors** to link Problem → Model → Outcome (use the "Problem → Solution → Outcome Map" above as the source of truth).
6. Add the **Cross-cutting capabilities** frame underneath as a foundation layer.

> Tip: color-code by block (A=blue, B=teal, C=green, D=lime, E=orange, F=red, G=purple) so the model side of the board reads like the architecture diagram.
