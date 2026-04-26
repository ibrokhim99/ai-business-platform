from fastapi import APIRouter, Query
from app.dependencies import RegistryDep, UserDep, RedisDep, DBDep
from app.services.prediction_service import PredictionService
from app.schemas.block_d import (
    ViabilityCheckIn, UnitEconomicsIn, ROIEstimatorIn,
    RentalBurdenIn, CashFlowSimIn, COGSMarginIn,
)

router = APIRouter(prefix="/financial", tags=["Block D — Financial Viability"])


def _svc(r, redis, db): return PredictionService(r, redis, db)


@router.post("/viability-check")
async def viability_check(body: ViabilityCheckIn, registry: RegistryDep, user: UserDep,
                          redis: RedisDep, db: DBDep,
                          explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-D1", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/unit-economics")
async def unit_economics(body: UnitEconomicsIn, registry: RegistryDep, user: UserDep,
                         redis: RedisDep, db: DBDep,
                         explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-D2", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/roi-estimator")
async def roi_estimator(body: ROIEstimatorIn, registry: RegistryDep, user: UserDep,
                        redis: RedisDep, db: DBDep,
                        explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-D3", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/rental-burden")
async def rental_burden(body: RentalBurdenIn, registry: RegistryDep, user: UserDep,
                        redis: RedisDep, db: DBDep,
                        explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-D4", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/cash-flow-simulator")
async def cash_flow_sim(body: CashFlowSimIn, registry: RegistryDep, user: UserDep,
                        redis: RedisDep, db: DBDep,
                        explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-D5", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/cogs-margin")
async def cogs_margin(body: COGSMarginIn, registry: RegistryDep, user: UserDep,
                      redis: RedisDep, db: DBDep,
                      explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-D6", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()
