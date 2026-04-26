from fastapi import APIRouter, Query
from app.dependencies import RegistryDep, RedisDep, DBDep, require_role
from app.services.prediction_service import PredictionService
from app.schemas.block_h import (
    CACPredictorIn, LTVCACRatioIn, ChannelAttributionIn,
    PromoUpliftIn, OptimalPricingIn, LookalikeAudienceIn,
)

router = APIRouter(prefix="/marketing", tags=["Block H — Marketing & Customer Acquisition"])
_analyst = require_role("bank_analyst", "admin")


def _svc(r, redis, db): return PredictionService(r, redis, db)


@router.post("/cac-predictor")
async def cac_predictor(body: CACPredictorIn, registry: RegistryDep,
                        redis: RedisDep, db: DBDep, user=_analyst,
                        explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-H1", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/ltv-cac-ratio")
async def ltv_cac_ratio(body: LTVCACRatioIn, registry: RegistryDep,
                        redis: RedisDep, db: DBDep, user=_analyst,
                        explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-H2", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/channel-attribution")
async def channel_attribution(body: ChannelAttributionIn, registry: RegistryDep,
                              redis: RedisDep, db: DBDep, user=_analyst,
                              explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-H3", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/promo-uplift")
async def promo_uplift(body: PromoUpliftIn, registry: RegistryDep,
                       redis: RedisDep, db: DBDep, user=_analyst,
                       explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-H4", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/optimal-pricing")
async def optimal_pricing(body: OptimalPricingIn, registry: RegistryDep,
                          redis: RedisDep, db: DBDep, user=_analyst,
                          explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-H5", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/lookalike-audience")
async def lookalike_audience(body: LookalikeAudienceIn, registry: RegistryDep,
                             redis: RedisDep, db: DBDep, user=_analyst,
                             explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-H6", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()
