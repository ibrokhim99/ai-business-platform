# AI Business Intelligence Platform

ML-powered decision support platform for banks — helping SMB clients open businesses, assess credit risk, optimise location, run marketing & operations, and detect fraud using 55 production-grade AI models across 10 analytical blocks.

---

## Overview

| Metric | Value |
|--------|-------|
| ML models | 55 (10 blocks) |
| API endpoints | 55+ |
| Tech stack | FastAPI · PostgreSQL · Redis · MLflow · Celery · Next.js 14 |
| Model status | All real implementations (no stubs) |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Next.js 14 Frontend  (localhost:3000)           │
│  TypeScript · Tailwind CSS · Role-gated UI       │
└───────────────────┬─────────────────────────────┘
                    │ REST / JSON
┌───────────────────▼─────────────────────────────┐
│  FastAPI Backend  (localhost:8000)               │
│  55 ML models · JWT auth · Rate limiting         │
│  Prometheus metrics · Request-ID tracing         │
└───┬───────────┬──────────────┬───────────────────┘
    │           │              │
┌───▼──┐  ┌────▼────┐  ┌──────▼──────┐
│ PG16 │  │ Redis 7 │  │   MLflow    │
│ audit│  │  cache  │  │  registry   │
└──────┘  └─────────┘  └─────────────┘
                              │
                        ┌─────▼──────┐
                        │   MinIO    │
                        │ artifacts  │
                        └────────────┘
```

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Node.js 18+ (for frontend dev)

### 1 — Start all backend services

```bash
docker compose up -d
```

Services started:
- `http://localhost:8000` — FastAPI (Swagger at `/docs`)
- `http://localhost:5000` — MLflow UI
- `http://localhost:5555` — Flower (Celery monitor)
- `http://localhost:9001` — MinIO console

### 2 — Run database migrations

```bash
make migrate
```

### 3 — Start the frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 4 — Login

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@bank.uz` | `admin123` |
| Credit Officer | `officer@bank.uz` | `officer123` |
| Bank Analyst | `analyst@bank.uz` | `analyst123` |
| Customer | `customer@bank.uz` | `customer123` |

---

## ML Model Blocks

Full algorithm details: [`docs/ML_CATALOG.md`](docs/ML_CATALOG.md)

| Block | Name | Models | Key Algorithms |
|-------|------|--------|----------------|
| A | Market Analysis & Capacity | 6 | Bayesian regression, XGBoost, haversine graph |
| B | Forecasting & Demand | 6 | ExponentialSmoothing, ARIMA, ruptures PELT |
| C | Location Assessment & Traffic | 6 | GradientBoosting, Newton gravity, shapely |
| D | Financial Viability | 6 | Monte Carlo (500 runs), DCF, scipy IRR |
| E | Competition & Risks | 5 | XGBoost churn, Kaplan-Meier, hedonic pricing |
| F | Credit & Banking Products | 5 | LightGBM scorer, IsolationForest, annuity math |
| G | Social Profile & Audience | 5 | K-means, gravity model, IDW interpolation |
| H | Marketing & Customer Acquisition | 6 | GradientBoosting CAC, Shapley attribution, two-model uplift |
| I | Operations & Supply Chain | 5 | EOQ + safety stock, Normal stockout, Clarke-Wright VRP |
| J | Fraud, AML & Identity | 5 | IsolationForest, LightGBM, XGBoost, FATF rule typologies |

---

## API Reference

### Authentication

```http
POST /api/v1/auth/token
Content-Type: application/json

{"email": "admin@bank.uz", "password": "admin123"}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 3600
}
```

All prediction endpoints require:
```
Authorization: Bearer <access_token>
```

Additional auth endpoints:
- `POST /api/v1/auth/register` — create new user
- `POST /api/v1/auth/refresh` — refresh access token
- `GET  /api/v1/auth/me` — current user info

### Prediction envelope

Every model endpoint returns the same envelope:

```json
{
  "model_id": "M-F1",
  "version": "1.0.0",
  "is_stub": false,
  "prediction": { ... },
  "explanation": null,
  "latency_ms": 12,
  "request_id": "uuid"
}
```

Add `?explain=true` to any endpoint to receive feature attribution alongside the prediction.

### Block A — Market Analysis (`/api/v1/market-analysis/`)

| Endpoint | Model | Input |
|----------|-------|-------|
| `POST /market-sizing` | M-A1 | region_id, mcc_code, population, avg_income |
| `POST /gap-analysis` | M-A2 | region_id, mcc_code, normative_density, actual_count, population |
| `POST /saturation-index` | M-A3 | region_id, mcc_code, competitor_count, population, avg_revenue_per_outlet |
| `POST /wallet-share` | M-A4 | region_id, mcc_code, population, avg_monthly_spend, competitor_count |
| `POST /niche-opportunity` | M-A5 | region_id, mcc_code, population, avg_income, competitor_count, growth_rate_pct |
| `POST /cross-niche` | M-A6 | new_mcc_code, location_lat, location_lon, radius_m, adjacent_mcc_codes |

### Block B — Forecasting (`/api/v1/forecasting/`)

| Endpoint | Model | Input |
|----------|-------|-------|
| `POST /demand-forecast` | M-B1 | region_id, mcc_code, horizon_months, base_monthly_revenue |
| `POST /seasonality` | M-B2 | mcc_code, region_id, year |
| `POST /population-dynamics` | M-B3 | region_id, horizon_years |
| `POST /income-trend` | M-B4 | region_id, horizon_months, current_avg_income |
| `POST /mcc-trend` | M-B5 | mcc_code, region_id, lookback_months |
| `POST /business-registration` | M-B6 | region_id, mcc_code, horizon_months |

### Block C — Location (`/api/v1/location/`)

| Endpoint | Model | Input |
|----------|-------|-------|
| `POST /score` | M-C1 | lat, lon, mcc_code, radius_m |
| `POST /traffic-scoring` | M-C2 | lat, lon, radius_m |
| `POST /isochrone-demand` | M-C3 | lat, lon, walk_minutes, mcc_code |
| `POST /street-vitality` | M-C4 | lat, lon, radius_m |
| `POST /anchor-effect` | M-C5 | lat, lon, radius_m |
| `POST /visibility-score` | M-C6 | lat, lon, facade_direction_deg |

### Block D — Financial (`/api/v1/financial/`)

| Endpoint | Model | Input |
|----------|-------|-------|
| `POST /viability-check` | M-D1 | mcc_code, region_id, monthly_revenue_estimate, monthly_fixed_costs, initial_investment, monthly_rent |
| `POST /unit-economics` | M-D2 | mcc_code, avg_transaction_value, monthly_transactions, customer_acquisition_cost, monthly_churn_rate_pct, gross_margin_pct |
| `POST /roi-estimator` | M-D3 | initial_investment, monthly_net_cash_flow, discount_rate_annual_pct, horizon_years |
| `POST /rental-burden` | M-D4 | mcc_code, monthly_revenue_estimate, monthly_rent |
| `POST /cash-flow-simulator` | M-D5 | mcc_code, region_id, initial_investment, monthly_revenue_base, monthly_fixed_costs, cogs_pct, growth_rate_monthly_pct, horizon_months |
| `POST /cogs-margin` | M-D6 | mcc_code, monthly_revenue, region_id |

### Block E — Competition (`/api/v1/competition/`) — `bank_analyst` / `admin` only

| Endpoint | Model | Input |
|----------|-------|-------|
| `POST /competitor-intelligence` | M-E1 | lat, lon, mcc_code |
| `POST /churn-prediction` | M-E2 | mcc_code, region_id, monthly_revenue, initial_investment, owner_experience_years, location_score, competition_count |
| `POST /regulatory-risk` | M-E3 | mcc_code, region_id, business_age_months |
| `POST /entry-barrier` | M-E4 | mcc_code, region_id, initial_investment |
| `POST /price-pressure` | M-E5 | mcc_code, region_id, target_price, competitor_avg_price |

### Block F — Credit (`/api/v1/credit/`) — `credit_officer` / `admin` only

| Endpoint | Model | Input |
|----------|-------|-------|
| `POST /risk-score` | M-F1 | customer_id, mcc_code, region_id, lat, lon, monthly_revenue_estimate, requested_loan_amount, business_age_months, owner_credit_history_score, collateral_value |
| `POST /loan-sizing` | M-F2 | monthly_net_cashflow, monthly_revenue, existing_debt_monthly, loan_term_months, interest_rate_annual_pct |
| `POST /dti-predictor` | M-F3 | mcc_code, region_id, initial_monthly_revenue, proposed_loan_amount, loan_term_months, interest_rate_annual_pct |
| `POST /npl-warning` | M-F4 | customer_id, loan_id, months_since_disbursement, payment_delays_count, revenue_trend_3m_pct, current_dti, location_score |
| `POST /product-recommender` | M-F5 | customer_id, mcc_code, monthly_revenue, business_age_months, existing_products, credit_score |

### Block G — Social Profile (`/api/v1/social/`)

| Endpoint | Model | Input |
|----------|-------|-------|
| `POST /customer-profiler` | M-G1 | lat, lon, radius_m, mcc_code |
| `POST /day-population` | M-G2 | lat, lon, radius_m, hour_of_day, day_of_week |
| `POST /behavior-classifier` | M-G3 | lat, lon, radius_m, mcc_code |
| `POST /brand-affinity` | M-G4 | lat, lon, radius_m, mcc_code |
| `POST /spending-power` | M-G5 | lat, lon, radius_m |

### Other endpoints

```
GET  /api/v1/health         — liveness check
GET  /api/v1/readiness      — readiness (DB + Redis)
GET  /api/v1/models         — full model catalog (39 entries)
GET  /api/v1/models/{id}    — single model metadata
POST /api/v1/models/{id}/retrain — enqueue Celery retraining job
GET  /metrics               — Prometheus metrics
```

---

## Role-Based Access Control

| Role | Block A-D, G | Block E | Block F |
|------|-------------|---------|---------|
| `customer` | ✓ | ✗ | ✗ |
| `bank_analyst` | ✓ | ✓ | ✗ |
| `credit_officer` | ✓ | ✗ | ✓ |
| `admin` | ✓ | ✓ | ✓ |

---

## Frontend

The Next.js 14 frontend lives in `/frontend`.

### Pages

| Route | Description |
|-------|-------------|
| `/login` | JWT login form |
| `/dashboard` | Platform overview — 7 block cards |
| `/dashboard/block-a` | Market Analysis — 6 model tabs |
| `/dashboard/block-b` | Forecasting — 6 model tabs |
| `/dashboard/block-c` | Location Assessment — 6 model tabs |
| `/dashboard/block-d` | Financial Viability — 6 model tabs |
| `/dashboard/block-e` | Competition & Risks — role-gated |
| `/dashboard/block-f` | Credit & Banking — role-gated |
| `/dashboard/block-g` | Social Profile — 5 model tabs |

### Features
- Dark professional fintech design (slate-900 / blue-600)
- Explain toggle (`?explain=true`) on every prediction form
- `is_stub` badge — yellow (STUB) / green (LIVE) on every response
- Latency display on every result
- Auth context with JWT storage and automatic route guards

---

## Caching

Redis caches predictions per block with these TTLs:

| Block | TTL | Notes |
|-------|-----|-------|
| A — Market Analysis | 6 h | |
| B — Forecasting | 6 h | |
| C — Location | 24 h | M-C2 (Traffic) never cached |
| D — Financial | 6 h | |
| E — Competition | 6 h | |
| F — Credit | 15 min | Frequent re-scoring |
| G — Social | 6 h | M-G2 (Day Population) never cached |

Cache key: `SHA-256(model_id + version + explain_flag + sorted_input_json)`

---

## Development

```bash
# Run tests
make test

# Lint
make lint

# Apply DB migrations
make migrate

# Enqueue model retraining
make train MODEL=M-F1

# Seed test data
make seed
```

### Running tests locally

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term
```

### Environment variables

Copy `.env.example` to `.env` and adjust:

```env
DATABASE_URL=postgresql+asyncpg://aibp:aibp@localhost:5432/aibp
REDIS_URL=redis://localhost:6379/0
MLFLOW_TRACKING_URI=http://localhost:5000
SECRET_KEY=change-me-in-production
```

---

## Project Structure

```
AI-Business-Platform/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (auth + 7 blocks)
│   │   ├── core/         # security, logging, exceptions
│   │   ├── ml/
│   │   │   ├── base.py           # BaseMLModel ABC
│   │   │   ├── registry.py       # auto-discovery & singleton
│   │   │   ├── explainability.py # SHAP service
│   │   │   ├── mlflow_client.py  # experiment & artifact management
│   │   │   ├── block_a/ … block_g/  # 39 model implementations
│   │   ├── models/       # SQLAlchemy ORM (User, Business, Audit, Registry)
│   │   ├── schemas/      # Pydantic input/output schemas
│   │   ├── services/     # PredictionService, TrainingService
│   │   └── tasks/        # Celery training tasks
│   ├── alembic/          # DB migrations
│   └── tests/            # pytest integration tests
├── frontend/
│   └── src/
│       ├── app/          # Next.js App Router pages
│       ├── lib/          # api.ts, auth.ts
│       └── types/        # TypeScript interfaces
├── docker/               # Dockerfiles + nginx config
├── docker-compose.yml
└── Makefile
```

---

## Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0 | ✅ Done | 39 stub API endpoints, Docker Compose, OpenAPI docs |
| 1 | ✅ Done | Redis cache, PostgreSQL audit log, MLflow client, CI pipeline |
| 2 | ✅ Done | Real ML algorithms, Next.js frontend, DB-connected auth |
| 3 | Planned | Real training data, SHAP explainability, model versioning UI |
