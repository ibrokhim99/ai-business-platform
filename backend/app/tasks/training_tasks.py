"""Celery tasks for async model retraining."""
from __future__ import annotations

from app.tasks.celery_app import celery_app
from app.core.logging import get_logger

log = get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def retrain_model(self, model_id: str, dataset_path: str | None = None, job_id: str | None = None):
    """
    Retrain a single model and register the artifact in MLflow.

    Steps (when a real trainer is implemented):
      1. Load dataset from dataset_path (S3/MinIO).
      2. Instantiate the model class from the registry.
      3. Call model.train(df) — returns a fitted sklearn-compatible estimator.
      4. Open an MLflow run, log params + metrics.
      5. Register the artifact with log_model_artifact().
      6. Promote to Production via promote_to_production().
      7. Update ModelVersion table in Postgres.
      8. Invalidate the ModelRegistry instance cache so the next request gets the new model.

    Currently runs as a stub — logs intent but performs no actual training.
    """
    log.info("retrain_start", model_id=model_id, dataset_path=dataset_path, job_id=job_id)
    try:
        from app.ml import mlflow_client

        block = model_id.split("-")[1] if "-" in model_id else "A"

        with mlflow_client.start_run(
            model_id,
            run_name=f"{model_id}_retrain_{job_id or 'manual'}",
            tags={"triggered_by": "celery", "job_id": job_id or ""},
        ) as run:
            if run is not None:
                import mlflow
                # Stub: log placeholder metrics so the run isn't empty
                mlflow.log_params({"dataset_path": dataset_path or "none", "is_stub": "true"})
                mlflow.log_metrics({"accuracy": 0.0, "note": 0})
                log.info("mlflow_stub_run_logged", model_id=model_id, run_id=run.info.run_id)
            else:
                log.info("mlflow_unavailable_stub_only", model_id=model_id)

        log.info(
            "retrain_complete_stub",
            model_id=model_id,
            job_id=job_id,
            note="Stub — no actual training performed",
        )
        return {"status": "stub_complete", "model_id": model_id, "job_id": job_id}

    except Exception as exc:
        log.error("retrain_failed", model_id=model_id, error=str(exc))
        raise self.retry(exc=exc)
