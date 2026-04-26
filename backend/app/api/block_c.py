from fastapi import APIRouter, Query
from app.dependencies import RegistryDep, UserDep, RedisDep, DBDep
from app.services.prediction_service import PredictionService
from app.schemas.block_c import (
    LocationScoreIn, TrafficScoringIn, IsochroneDemandIn,
    StreetVitalityIn, AnchorEffectIn, VisibilityScoreIn,
)

router = APIRouter(prefix="/location", tags=["Block C — Location Assessment"])


def _svc(r, redis, db): return PredictionService(r, redis, db)


@router.post("/score")
async def location_score(body: LocationScoreIn, registry: RegistryDep, user: UserDep,
                         redis: RedisDep, db: DBDep,
                         explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-C1", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/traffic-scoring")
async def traffic_scoring(body: TrafficScoringIn, registry: RegistryDep, user: UserDep,
                          redis: RedisDep, db: DBDep,
                          explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-C2", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/isochrone-demand")
async def isochrone_demand(body: IsochroneDemandIn, registry: RegistryDep, user: UserDep,
                           redis: RedisDep, db: DBDep,
                           explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-C3", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/street-vitality")
async def street_vitality(body: StreetVitalityIn, registry: RegistryDep, user: UserDep,
                          redis: RedisDep, db: DBDep,
                          explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-C4", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/anchor-effect")
async def anchor_effect(body: AnchorEffectIn, registry: RegistryDep, user: UserDep,
                        redis: RedisDep, db: DBDep,
                        explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-C5", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/visibility-score")
async def visibility_score(body: VisibilityScoreIn, registry: RegistryDep, user: UserDep,
                           redis: RedisDep, db: DBDep,
                           explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-C6", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()
