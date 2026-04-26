from fastapi import APIRouter, Query
from app.dependencies import RegistryDep, UserDep, RedisDep, DBDep
from app.services.prediction_service import PredictionService
from app.schemas.block_a import (
    MarketSizingIn, GapAnalysisIn, SaturationIndexIn,
    WalletShareIn, NicheOpportunityIn, CrossNicheIn,
)

router = APIRouter(prefix="/market-analysis", tags=["Block A — Market Analysis"])


def _svc(registry, redis, db): return PredictionService(registry, redis, db)


@router.post("/market-sizing")
async def market_sizing(body: MarketSizingIn, registry: RegistryDep, user: UserDep,
                        redis: RedisDep, db: DBDep,
                        explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-A1", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/gap-analysis")
async def gap_analysis(body: GapAnalysisIn, registry: RegistryDep, user: UserDep,
                       redis: RedisDep, db: DBDep,
                       explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-A2", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/saturation-index")
async def saturation_index(body: SaturationIndexIn, registry: RegistryDep, user: UserDep,
                           redis: RedisDep, db: DBDep,
                           explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-A3", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/wallet-share")
async def wallet_share(body: WalletShareIn, registry: RegistryDep, user: UserDep,
                       redis: RedisDep, db: DBDep,
                       explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-A4", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/niche-opportunity")
async def niche_opportunity(body: NicheOpportunityIn, registry: RegistryDep, user: UserDep,
                            redis: RedisDep, db: DBDep,
                            explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-A5", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/cross-niche")
async def cross_niche(body: CrossNicheIn, registry: RegistryDep, user: UserDep,
                      redis: RedisDep, db: DBDep,
                      explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-A6", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()
