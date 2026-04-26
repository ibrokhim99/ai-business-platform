from fastapi import APIRouter, Query
from app.dependencies import RegistryDep, UserDep, RedisDep, DBDep
from app.services.prediction_service import PredictionService
from app.schemas.block_b import (
    DemandForecastIn, SeasonalityIn, PopulationDynamicsIn,
    IncomeTrendIn, MCCTrendIn, BusinessRegistrationIn,
)

router = APIRouter(prefix="/forecasting", tags=["Block B — Forecasting & Demand"])


def _svc(r, redis, db): return PredictionService(r, redis, db)


@router.post("/demand-forecast")
async def demand_forecast(body: DemandForecastIn, registry: RegistryDep, user: UserDep,
                          redis: RedisDep, db: DBDep,
                          explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-B1", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/seasonality")
async def seasonality(body: SeasonalityIn, registry: RegistryDep, user: UserDep,
                      redis: RedisDep, db: DBDep,
                      explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-B2", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/population-dynamics")
async def population_dynamics(body: PopulationDynamicsIn, registry: RegistryDep, user: UserDep,
                              redis: RedisDep, db: DBDep,
                              explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-B3", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/income-trend")
async def income_trend(body: IncomeTrendIn, registry: RegistryDep, user: UserDep,
                       redis: RedisDep, db: DBDep,
                       explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-B4", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/mcc-trend")
async def mcc_trend(body: MCCTrendIn, registry: RegistryDep, user: UserDep,
                    redis: RedisDep, db: DBDep,
                    explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-B5", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/business-registration")
async def business_registration(body: BusinessRegistrationIn, registry: RegistryDep, user: UserDep,
                                redis: RedisDep, db: DBDep,
                                explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-B6", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()
