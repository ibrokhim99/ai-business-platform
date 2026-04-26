from fastapi import APIRouter, Query
from app.dependencies import RegistryDep, RedisDep, DBDep, require_role
from app.services.prediction_service import PredictionService
from app.schemas.block_e import (
    CompetitorIntelIn, ChurnPredictionIn, RegulatoryRiskIn,
    EntryBarrierIn, PricePressureIn,
)

router = APIRouter(prefix="/competition", tags=["Block E — Competition & Risks"])
_analyst = require_role("bank_analyst", "credit_officer", "admin")


def _svc(r, redis, db): return PredictionService(r, redis, db)


@router.post("/competitor-intelligence")
async def competitor_intel(body: CompetitorIntelIn, registry: RegistryDep,
                           redis: RedisDep, db: DBDep, user=_analyst,
                           explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-E1", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/churn-prediction")
async def churn_prediction(body: ChurnPredictionIn, registry: RegistryDep,
                           redis: RedisDep, db: DBDep, user=_analyst,
                           explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-E2", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/regulatory-risk")
async def regulatory_risk(body: RegulatoryRiskIn, registry: RegistryDep,
                          redis: RedisDep, db: DBDep, user=_analyst,
                          explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-E3", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/entry-barrier")
async def entry_barrier(body: EntryBarrierIn, registry: RegistryDep,
                        redis: RedisDep, db: DBDep, user=_analyst,
                        explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-E4", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/price-pressure")
async def price_pressure(body: PricePressureIn, registry: RegistryDep,
                         redis: RedisDep, db: DBDep, user=_analyst,
                         explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-E5", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()
