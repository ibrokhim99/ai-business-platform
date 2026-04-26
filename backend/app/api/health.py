from fastapi import APIRouter
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


@router.get("/readiness", response_model=HealthResponse)
async def readiness():
    return HealthResponse(status="ok", services={"api": "up"})
