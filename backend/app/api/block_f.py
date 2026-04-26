from fastapi import APIRouter, Query
from app.dependencies import RegistryDep, RedisDep, DBDep, require_role
from app.services.prediction_service import PredictionService
from app.schemas.block_f import (
    CreditRiskIn, LoanSizingIn, DTIPredictorIn,
    NPLWarningIn, ProductRecommenderIn,
)

router = APIRouter(prefix="/credit", tags=["Block F — Credit & Banking Products"])
_officer = require_role("credit_officer", "admin")


def _svc(r, redis, db): return PredictionService(r, redis, db)


@router.post("/risk-score")
async def credit_risk(body: CreditRiskIn, registry: RegistryDep,
                      redis: RedisDep, db: DBDep, user=_officer,
                      explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-F1", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/loan-sizing")
async def loan_sizing(body: LoanSizingIn, registry: RegistryDep,
                      redis: RedisDep, db: DBDep, user=_officer,
                      explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-F2", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/dti-predictor")
async def dti_predictor(body: DTIPredictorIn, registry: RegistryDep,
                        redis: RedisDep, db: DBDep, user=_officer,
                        explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-F3", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/npl-warning")
async def npl_warning(body: NPLWarningIn, registry: RegistryDep,
                      redis: RedisDep, db: DBDep, user=_officer,
                      explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-F4", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/product-recommender")
async def product_recommender(body: ProductRecommenderIn, registry: RegistryDep,
                              redis: RedisDep, db: DBDep, user=_officer,
                              explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-F5", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()
