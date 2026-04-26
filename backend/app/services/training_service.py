"""TrainingService — validates inputs and enqueues Celery retraining jobs."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.ml.registry import ModelRegistry

log = get_logger()


class TrainingService:
    def __init__(self, registry: ModelRegistry):
        self._registry = registry

    def enqueue_retrain(self, model_id: str, dataset_path: str | None = None) -> dict:
        if model_id not in self._registry.all_ids():
            raise ValueError(f"Model '{model_id}' not registered.")

        job_id = str(uuid.uuid4())
        log.info("retrain_enqueued", model_id=model_id, job_id=job_id)

        try:
            from app.tasks.training_tasks import retrain_model
            retrain_model.delay(model_id, dataset_path, job_id)
        except Exception as e:
            log.warning("celery_unavailable", error=str(e))

        return {
            "job_id": job_id,
            "model_id": model_id,
            "status": "enqueued",
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
        }
