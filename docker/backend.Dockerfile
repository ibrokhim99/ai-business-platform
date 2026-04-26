# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build
RUN pip install --upgrade pip hatchling

COPY pyproject.toml .
RUN pip install --no-cache-dir ".[dev]" --target /opt/venv 2>&1 | tail -5 || true
# Install core deps only (excludes heavy ML libs for faster dev build)
RUN pip install --no-cache-dir \
    fastapi==0.111.0 uvicorn[standard]==0.29.0 python-multipart==0.0.9 \
    pydantic==2.7.1 pydantic-settings==2.2.1 \
    sqlalchemy==2.0.30 asyncpg==0.29.0 alembic==1.13.1 \
    python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4 \
    redis[hiredis]==5.0.4 celery==5.4.0 \
    numpy==1.26.4 scipy==1.13.0 scikit-learn==1.4.2 pandas==2.2.2 \
    xgboost==2.0.3 lightgbm==4.3.0 statsmodels==0.14.2 ruptures==1.1.9 \
    structlog==24.1.0 python-dotenv==1.0.1 orjson==3.10.3 \
    slowapi==0.1.9 prometheus-fastapi-instrumentator==7.0.0 \
    httpx==0.27.0 pytest==8.2.0 pytest-asyncio==0.23.6

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Native libs required by lightgbm/xgboost
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN chown -R appuser:appgroup /app
USER appuser

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
