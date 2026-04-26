from fastapi import APIRouter, Query
from app.dependencies import RegistryDep, RedisDep, DBDep, require_role
from app.services.prediction_service import PredictionService
from app.schemas.block_j import (
    TransactionAnomalyIn, MerchantFraudIn, AMLPatternIn,
    SyntheticIdentityIn, ApplicationFraudIn,
)

router = APIRouter(prefix="/fraud", tags=["Block J — Fraud, AML & Identity"])
_officer = require_role("credit_officer", "admin")


def _svc(r, redis, db): return PredictionService(r, redis, db)


@router.post("/transaction-anomaly")
async def transaction_anomaly(body: TransactionAnomalyIn, registry: RegistryDep,
                              redis: RedisDep, db: DBDep, user=_officer,
                              explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-J1", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/merchant-fraud")
async def merchant_fraud(body: MerchantFraudIn, registry: RegistryDep,
                         redis: RedisDep, db: DBDep, user=_officer,
                         explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-J2", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/aml-pattern")
async def aml_pattern(body: AMLPatternIn, registry: RegistryDep,
                      redis: RedisDep, db: DBDep, user=_officer,
                      explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-J3", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/synthetic-identity")
async def synthetic_identity(body: SyntheticIdentityIn, registry: RegistryDep,
                             redis: RedisDep, db: DBDep, user=_officer,
                             explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-J4", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/application-fraud")
async def application_fraud(body: ApplicationFraudIn, registry: RegistryDep,
                            redis: RedisDep, db: DBDep, user=_officer,
                            explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-J5", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()
