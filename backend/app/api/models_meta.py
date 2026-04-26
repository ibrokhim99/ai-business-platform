from fastapi import APIRouter, HTTPException

from app.dependencies import RegistryDep, UserDep, require_role
from app.ml import mlflow_client
from app.schemas.common import ModelCatalogResponse, ModelMetadataOut, TrainingJobOut
from app.services.training_service import TrainingService

router = APIRouter(prefix="/models", tags=["Model Catalog"])
_admin = require_role("admin")


@router.get("", response_model=ModelCatalogResponse)
async def list_models(registry: RegistryDep, _user: UserDep):
    all_meta = registry.list_all()
    return ModelCatalogResponse(
        total=len(all_meta),
        models=[ModelMetadataOut(**m.model_dump()) for m in all_meta],
    )


@router.get("/{model_id}", response_model=ModelMetadataOut)
async def get_model(model_id: str, registry: RegistryDep, _user: UserDep):
    model = registry.get(model_id)
    meta = model.get_metadata()
    out = ModelMetadataOut(**meta.model_dump())
    # Attach MLflow version history if available
    out.mlflow_versions = mlflow_client.list_model_versions(model_id)
    return out


@router.post("/{model_id}/retrain", response_model=TrainingJobOut)
async def retrain_model_endpoint(model_id: str, registry: RegistryDep, user=_admin):
    svc = TrainingService(registry)
    try:
        job = svc.enqueue_retrain(model_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return TrainingJobOut(**job)
