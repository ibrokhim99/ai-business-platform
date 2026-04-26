"""
FastAPI application factory — Phase 1 wired version.
Adds: Redis, request-ID middleware, Prometheus metrics, slowapi rate limiting.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIDMiddleware
from app.core.redis_client import init_redis, close_redis
from app.ml.registry import get_registry
from app.services.llm_provider import get_llm_client
from app.api.router import api_router

log = get_logger()

# ── Rate limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    configure_logging(settings.log_level)
    log.info("startup", environment=settings.environment)

    # Redis (non-fatal — predictions work without cache)
    try:
        redis = await init_redis()
        app.state.redis = redis
        log.info("redis_connected", url=settings.redis_url)
    except Exception as e:
        app.state.redis = None
        log.warning("redis_unavailable", error=str(e), note="Predictions will run uncached")

    # Model registry — auto-discovers and loads all 39 stub models
    registry = get_registry()
    app.state.registry = registry
    log.info("registry_loaded", model_count=len(registry))

    # LLM client (non-fatal — chat endpoint will surface a clear error if unavailable)
    llm = get_llm_client()
    app.state.llm = llm
    provider = settings.llm_provider
    if await llm.health():
        log.info("llm_ready", provider=provider, model=llm.model)
    else:
        log.warning(
            "llm_unavailable",
            provider=provider,
            model=llm.model,
            note="Chat endpoint will fail until the provider is reachable",
        )

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    await close_redis()
    log.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Business Platform",
        description=(
            "39-model AI Business Intelligence Platform for bank customers and credit officers.\n\n"
            "**Blocks:**\n"
            "- A: Market Analysis (6 models)\n"
            "- B: Forecasting & Demand (6 models)\n"
            "- C: Location Assessment (6 models)\n"
            "- D: Financial Viability (6 models)\n"
            "- E: Competition & Risks (5 models)\n"
            "- F: Credit & Banking Products (5 models)\n"
            "- G: Social Profile & Audience (5 models)\n\n"
            "All endpoints support `?explain=true` for SHAP feature attribution."
        ),
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Rate limiting ──────────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Middleware (order matters — outermost = last to execute on request) ───
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
    )

    # ── Prometheus metrics ─────────────────────────────────────────────────────
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator(
            should_group_status_codes=True,
            excluded_handlers=["/health", "/readiness", "/metrics"],
        ).instrument(app).expose(app, endpoint="/metrics")
        log.info("prometheus_enabled")
    except ImportError:
        log.warning("prometheus_not_installed", note="pip install prometheus-fastapi-instrumentator")

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.api_prefix)

    # Health at root (no prefix) for load balancer probes
    from app.api.health import router as health_router
    app.include_router(health_router)

    # ── Global exception handler ───────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
