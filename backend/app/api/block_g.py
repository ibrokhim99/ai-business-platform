from fastapi import APIRouter, Query
from app.dependencies import RegistryDep, UserDep, RedisDep, DBDep
from app.services.prediction_service import PredictionService
from app.schemas.block_g import (
    CustomerProfilerIn, DayPopulationIn, BehaviorClassifierIn,
    BrandAffinityIn, SpendingPowerIn,
)

router = APIRouter(prefix="/social", tags=["Block G — Social Profile"])


def _svc(r, redis, db): return PredictionService(r, redis, db)


@router.post("/customer-profiler")
async def customer_profiler(body: CustomerProfilerIn, registry: RegistryDep, user: UserDep,
                            redis: RedisDep, db: DBDep,
                            explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-G1", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/day-population")
async def day_population(body: DayPopulationIn, registry: RegistryDep, user: UserDep,
                         redis: RedisDep, db: DBDep,
                         explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-G2", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/behavior-classifier")
async def behavior_classifier(body: BehaviorClassifierIn, registry: RegistryDep, user: UserDep,
                              redis: RedisDep, db: DBDep,
                              explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-G3", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/brand-affinity")
async def brand_affinity(body: BrandAffinityIn, registry: RegistryDep, user: UserDep,
                         redis: RedisDep, db: DBDep,
                         explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-G4", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/spending-power")
async def spending_power(body: SpendingPowerIn, registry: RegistryDep, user: UserDep,
                         redis: RedisDep, db: DBDep,
                         explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-G5", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()
