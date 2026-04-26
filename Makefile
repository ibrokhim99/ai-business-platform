.PHONY: dev down build test migrate seed train lint format help

# ─── Development ─────────────────────────────────────────────────────────
dev:
	docker compose up --build

down:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f backend

# ─── Database ─────────────────────────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head

makemigration:
	docker compose exec backend alembic revision --autogenerate -m "$(MSG)"

seed:
	docker compose exec backend python scripts/seed_db.py

# ─── Testing ──────────────────────────────────────────────────────────────
test:
	docker compose exec backend pytest tests/ -v --cov=app --cov-report=term-missing

test-unit:
	docker compose exec backend pytest tests/unit/ -v

test-integration:
	docker compose exec backend pytest tests/integration/ -v

load-test:
	docker compose exec backend locust -f tests/load/locustfile.py --headless -u 50 -r 5 --run-time 60s

# ─── ML Training ──────────────────────────────────────────────────────────
train:
	@if [ -z "$(MODEL)" ]; then echo "Usage: make train MODEL=M-F1"; exit 1; fi
	docker compose exec backend python -c "from app.tasks.training_tasks import retrain_model; retrain_model.delay('$(MODEL)')"

train-all:
	docker compose exec backend python scripts/retrain_all.py

# ─── Model Evaluation ─────────────────────────────────────────────────────
# Runs scripts/evaluate_models.py inside the live backend container, then
# copies the JSON+Markdown report back to ./reports/ on the host.
#
# ROWS=N         rows per model (default 100; 0 = full file)
# MODELS="..."   space-separated subset (e.g. MODELS="M-A1 M-J3")
# EXPLAIN=1      also call .explain() per row (slower)
evaluate:
	@mkdir -p reports
	docker compose cp data backend:/_eval_data
	docker compose exec backend python scripts/evaluate_models.py \
		--data-dir /_eval_data/test \
		--report-dir /tmp/_eval_reports \
		$(if $(ROWS),--rows $(ROWS),--rows 100) \
		$(if $(MODELS),--models $(MODELS),) \
		$(if $(EXPLAIN),--explain,)
	docker compose cp backend:/tmp/_eval_reports/. reports/
	@docker compose exec -u root backend rm -rf /tmp/_eval_reports /_eval_data

# ─── Code Quality ─────────────────────────────────────────────────────────
lint:
	cd backend && ruff check app/ tests/

format:
	cd backend && ruff format app/ tests/

typecheck:
	cd backend && mypy app/

# ─── Frontend ─────────────────────────────────────────────────────────────
fe-install:
	cd frontend && npm install

fe-gen-types:
	cd frontend && npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts

fe-dev:
	cd frontend && npm run dev

# ─── Help ─────────────────────────────────────────────────────────────────
help:
	@echo "Available targets:"
	@echo "  dev             Start all services with Docker Compose"
	@echo "  down            Stop and remove containers + volumes"
	@echo "  migrate         Run Alembic migrations"
	@echo "  makemigration   Generate new migration (MSG=description)"
	@echo "  test            Run full test suite"
	@echo "  train MODEL=X   Trigger retraining for model (e.g. M-F1)"
	@echo "  evaluate        Run scripts/evaluate_models.py on every block CSV (ROWS=N, MODELS=, EXPLAIN=1)"
	@echo "  lint            Run ruff linter"
	@echo "  format          Run ruff formatter"
	@echo "  fe-gen-types    Regenerate TypeScript API types from OpenAPI spec"
