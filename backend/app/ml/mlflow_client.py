"""
MLflow client wrapper — thin helpers around mlflow SDK.

Provides:
  - experiment_id()          → get-or-create an experiment by block name
  - start_run()              → context manager that yields an active MLflow run
  - log_model_artifact()     → save a sklearn/lgbm/xgb model and register it
  - get_latest_version()     → fetch the newest production-stage model URI
  - promote_to_production()  → transition a model version to Production stage

Usage in a training task:
    with mlflow_client.start_run("M-F1", "credit_risk_lgbm") as run:
        mlflow.log_params(params)
        mlflow.log_metrics({"auc": 0.91})
        mlflow_client.log_model_artifact(model, "M-F1", run)
"""
from __future__ import annotations

import contextlib
from typing import Any

from app.config import settings
from app.core.logging import get_logger

log = get_logger()

# ── Lazy MLflow import (optional dep in test environments) ─────────────────────
try:
    import mlflow
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient as _MlflowClient

    _client: _MlflowClient | None = None

    def _get_client() -> _MlflowClient:
        global _client
        if _client is None:
            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            _client = _MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
        return _client

    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False
    log.warning("mlflow_not_installed", note="MLflow features disabled; install mlflow to enable")


# ── Experiment helpers ─────────────────────────────────────────────────────────

_BLOCK_EXPERIMENT: dict[str, str] = {
    "A": "Block A — Market Analysis",
    "B": "Block B — Forecasting",
    "C": "Block C — Location Assessment",
    "D": "Block D — Financial Viability",
    "E": "Block E — Competition & Risks",
    "F": "Block F — Credit & Banking Products",
    "G": "Block G — Social Profile",
}


def experiment_id(block: str) -> str | None:
    """Return (or create) the MLflow experiment for *block*, e.g. 'F'."""
    if not HAS_MLFLOW:
        return None
    name = _BLOCK_EXPERIMENT.get(block.upper(), f"Block {block.upper()}")
    try:
        client = _get_client()
        exp = client.get_experiment_by_name(name)
        if exp:
            return exp.experiment_id
        return client.create_experiment(
            name,
            artifact_location=f"s3://{settings.minio_bucket}/{block.lower()}",
        )
    except Exception as e:
        log.warning("mlflow_experiment_error", block=block, error=str(e))
        return None


# ── Run context manager ────────────────────────────────────────────────────────

@contextlib.contextmanager
def start_run(model_id: str, run_name: str, tags: dict[str, str] | None = None):
    """
    Context manager that starts an MLflow run inside the correct experiment.

    Example::

        with mlflow_client.start_run("M-F1", "lgbm_v2") as run:
            mlflow.log_metric("auc", 0.93)
            run_id = run.info.run_id
    """
    if not HAS_MLFLOW:
        yield None
        return

    block = model_id.split("-")[1] if "-" in model_id else "A"
    exp_id = experiment_id(block)
    default_tags = {"model_id": model_id, "block": block}
    if tags:
        default_tags.update(tags)

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    with mlflow.start_run(
        experiment_id=exp_id,
        run_name=run_name,
        tags=default_tags,
    ) as run:
        log.info("mlflow_run_started", model_id=model_id, run_id=run.info.run_id)
        try:
            yield run
        except Exception:
            mlflow.set_tag("run_status", "FAILED")
            raise
        else:
            mlflow.set_tag("run_status", "SUCCESS")
        log.info("mlflow_run_finished", model_id=model_id, run_id=run.info.run_id)


# ── Model artifact helpers ─────────────────────────────────────────────────────

def log_model_artifact(
    model: Any,
    model_id: str,
    run,  # mlflow.ActiveRun
    flavor: str = "sklearn",
    registered_model_name: str | None = None,
) -> str | None:
    """
    Log a trained model artifact to MLflow.

    Returns the artifact URI, or None if MLflow is unavailable.

    Supported flavors: 'sklearn', 'lightgbm', 'xgboost', 'pytorch'.
    """
    if not HAS_MLFLOW or run is None:
        return None

    reg_name = registered_model_name or model_id
    artifact_path = f"model_{model_id.replace('-', '_').lower()}"

    try:
        if flavor == "sklearn":
            mlflow.sklearn.log_model(
                model, artifact_path, registered_model_name=reg_name
            )
        elif flavor == "lightgbm":
            import mlflow.lightgbm
            mlflow.lightgbm.log_model(
                model, artifact_path, registered_model_name=reg_name
            )
        elif flavor == "xgboost":
            import mlflow.xgboost
            mlflow.xgboost.log_model(
                model, artifact_path, registered_model_name=reg_name
            )
        elif flavor == "pytorch":
            import mlflow.pytorch
            mlflow.pytorch.log_model(
                model, artifact_path, registered_model_name=reg_name
            )
        else:
            log.warning("mlflow_unknown_flavor", flavor=flavor, model_id=model_id)
            return None

        artifact_uri = f"{run.info.artifact_uri}/{artifact_path}"
        log.info("mlflow_artifact_logged", model_id=model_id, uri=artifact_uri)
        return artifact_uri
    except Exception as e:
        log.error("mlflow_log_model_error", model_id=model_id, error=str(e))
        return None


# ── Model version queries ──────────────────────────────────────────────────────

def get_latest_version(model_id: str, stage: str = "Production") -> str | None:
    """
    Return the model URI for the latest *stage* version of *model_id*, or None.

    Example return value::
        's3://mlflow-artifacts/f/model_m_f1/artifacts/model'
    """
    if not HAS_MLFLOW:
        return None

    try:
        client = _get_client()
        versions = client.get_latest_versions(model_id, stages=[stage])
        if versions:
            v = versions[0]
            log.debug("mlflow_version_found", model_id=model_id, version=v.version, stage=stage)
            return v.source
        return None
    except Exception as e:
        log.warning("mlflow_get_version_error", model_id=model_id, error=str(e))
        return None


def promote_to_production(model_id: str, version: str) -> bool:
    """
    Transition *version* of *model_id* to Production stage.
    Archives any previous Production versions.
    Returns True on success.
    """
    if not HAS_MLFLOW:
        return False

    try:
        client = _get_client()
        client.transition_model_version_stage(
            name=model_id,
            version=version,
            stage="Production",
            archive_existing_versions=True,
        )
        log.info("mlflow_promoted", model_id=model_id, version=version)
        return True
    except Exception as e:
        log.error("mlflow_promote_error", model_id=model_id, version=version, error=str(e))
        return False


def list_model_versions(model_id: str) -> list[dict]:
    """Return all registered versions for *model_id* as dicts."""
    if not HAS_MLFLOW:
        return []

    try:
        client = _get_client()
        versions = client.search_model_versions(f"name='{model_id}'")
        return [
            {
                "version": v.version,
                "stage": v.current_stage,
                "run_id": v.run_id,
                "status": v.status,
                "source": v.source,
                "creation_timestamp": v.creation_timestamp,
            }
            for v in versions
        ]
    except Exception as e:
        log.warning("mlflow_list_versions_error", model_id=model_id, error=str(e))
        return []
