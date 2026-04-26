from fastapi import APIRouter, Query
from app.dependencies import RegistryDep, RedisDep, DBDep, require_role
from app.services.prediction_service import PredictionService
from app.schemas.block_i import (
    InventoryOptimizerIn, StockoutRiskIn, SupplierRiskIn,
    StaffingOptimizerIn, DeliveryRoutingIn,
)

router = APIRouter(prefix="/operations", tags=["Block I — Operations & Supply Chain"])
_ops = require_role("bank_analyst", "credit_officer", "admin")


def _svc(r, redis, db): return PredictionService(r, redis, db)


@router.post("/inventory-optimizer")
async def inventory_optimizer(body: InventoryOptimizerIn, registry: RegistryDep,
                              redis: RedisDep, db: DBDep, user=_ops,
                              explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-I1", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/stockout-risk")
async def stockout_risk(body: StockoutRiskIn, registry: RegistryDep,
                        redis: RedisDep, db: DBDep, user=_ops,
                        explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-I2", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/supplier-risk")
async def supplier_risk(body: SupplierRiskIn, registry: RegistryDep,
                        redis: RedisDep, db: DBDep, user=_ops,
                        explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-I3", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/staffing-optimizer")
async def staffing_optimizer(body: StaffingOptimizerIn, registry: RegistryDep,
                             redis: RedisDep, db: DBDep, user=_ops,
                             explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-I4", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()


@router.post("/delivery-routing")
async def delivery_routing(body: DeliveryRoutingIn, registry: RegistryDep,
                           redis: RedisDep, db: DBDep, user=_ops,
                           explain: bool = Query(False), version: str = Query("latest")):
    return (await _svc(registry, redis, db).predict(
        "M-I5", body, explain, version, user_id=user.user_id, user_role=user.role)).model_dump()
