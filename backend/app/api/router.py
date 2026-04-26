"""Root API router — mounts all sub-routers under /api/v1."""
from fastapi import APIRouter

from app.api import block_a, block_b, block_c, block_d, block_e, block_f, block_g
from app.api import block_h, block_i, block_j
from app.api import auth, chat, evidence, health, models_meta

api_router = APIRouter()

# Health (no prefix — lives at /)
api_router.include_router(health.router)

# Auth
api_router.include_router(auth.router)

# Model catalog
api_router.include_router(models_meta.router)

# Block routers (all under /api/v1 via prefix in main.py)
api_router.include_router(block_a.router)
api_router.include_router(block_b.router)
api_router.include_router(block_c.router)
api_router.include_router(block_d.router)
api_router.include_router(block_e.router)
api_router.include_router(block_f.router)
api_router.include_router(block_g.router)
api_router.include_router(block_h.router)
api_router.include_router(block_i.router)
api_router.include_router(block_j.router)

# Data transparency — surfaces the synthetic dataset rows behind predictions
api_router.include_router(evidence.router)

# LLM-driven chat (SSE). Sits in front of the 55 model endpoints.
api_router.include_router(chat.router)
