# Project Summary — AI Business Intelligence Platform

## What it is
An ML-powered decision support platform for banks. Helps SMB clients open businesses, assess credit risk, and choose locations using **39 production-grade AI models** organized into **7 analytical blocks**, exposed through **40+ REST endpoints** and a Next.js dashboard.

## Stack
- **Backend:** FastAPI · Python · SQLAlchemy (async) · Alembic · Celery
- **Frontend:** Next.js 14 · TypeScript · Tailwind CSS (App Router)
- **Data:** PostgreSQL 16 (audit log) · Redis 7 (prediction cache)
- **ML Ops:** MLflow (registry) · MinIO (artifacts) · Prometheus (metrics)
- **Infra:** Docker Compose · GitHub Actions CI · Makefile workflows

## Architecture
Next.js frontend → FastAPI backend (JWT auth, rate limiting, request-ID tracing) → Postgres + Redis + MLflow + MinIO. Each prediction returns a uniform envelope (`model_id`, `version`, `is_stub`, `prediction`, `explanation`, `latency_ms`, `request_id`). Adding `?explain=true` returns SHAP-style feature attributions.

## ML Model Blocks (39 models total)

| Block | Domain | # | Key algorithms |
|-------|--------|---|----------------|
| A | Market Analysis & Capacity | 6 | Bayesian regression, XGBoost, haversine graph |
| B | Forecasting & Demand | 6 | ExponentialSmoothing, ARIMA, ruptures PELT |
| C | Location Assessment & Traffic | 6 | GradientBoosting, Newton gravity, shapely |
| D | Financial Viability | 6 | Monte Carlo (500 runs), DCF, scipy IRR |
| E | Competition & Risks | 5 | XGBoost churn, Kaplan-Meier, hedonic pricing |
| F | Credit & Banking Products | 5 | LightGBM scorer, IsolationForest, annuity math |
| G | Social Profile & Audience | 5 | K-means, gravity model, IDW interpolation |

All models are real implementations — no stubs.

## Role-Based Access

| Role | Blocks A–D, G | Block E | Block F |
|------|---------------|---------|---------|
| customer | ✓ | ✗ | ✗ |
| bank_analyst | ✓ | ✓ | ✗ |
| credit_officer | ✓ | ✗ | ✓ |
| admin | ✓ | ✓ | ✓ |

## Caching
Per-block Redis TTLs: 6 h for most blocks, 24 h for Location, 15 min for Credit (frequent re-scoring). Real-time models (M-C2 traffic, M-G2 day-population) bypass cache. Cache key = `SHA-256(model_id + version + explain_flag + sorted_input_json)`.

## Frontend
JWT login + 7 dashboard pages (one per block) with model tabs, explain toggle, `is_stub` badge (LIVE/STUB), and latency display. Dark fintech theme (slate-900 / blue-600). Role-aware route guards hide blocks the user can't access.

## Development Workflow
- `docker compose up -d` — start backend stack (FastAPI, MLflow, MinIO, Flower, Postgres, Redis)
- `make migrate` — apply Alembic migrations
- `make test` / `make lint` / `make seed`
- `make train MODEL=M-F1` — enqueue Celery retraining

## Project Status

| Phase | Status | Scope |
|-------|--------|-------|
| 0 | ✅ Done | 39 stub endpoints, Docker Compose, OpenAPI |
| 1 | ✅ Done | Redis cache, audit log, MLflow client, CI |
| 2 | ✅ Done | Real ML algorithms, Next.js frontend, DB auth |
| 3 | Planned | Real training data, SHAP UI, model versioning UI |

## Layout
```
AI-Business-Platform/
├── backend/    FastAPI app, 39 ML models (block_a..block_g), Alembic, tests
├── frontend/   Next.js 14 App Router, TypeScript, Tailwind
├── data/       Test datasets (1000 rows per block) + generator
├── docs/       ML_CATALOG.md (per-model algorithm details)
├── docker/     Dockerfiles + nginx config
├── docker-compose.yml
└── Makefile
```

## Default Logins (dev only)
- admin@bank.uz / admin123
- officer@bank.uz / officer123
- analyst@bank.uz / analyst123
- customer@bank.uz / customer123
