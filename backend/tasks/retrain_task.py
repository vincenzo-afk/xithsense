"""Retrain Celery task."""
from backend.worker import celery_app


@celery_app.task(name="backend.tasks.retrain_task.retrain_models_task", bind=True)
def retrain_models_task(self, format: str = "T20", model_ids: list = None):
    try:
        # Import and run training pipeline
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "scripts/build_features.py", "--format", format],
            capture_output=True, text=True
        )
        return {"status": "success", "format": format, "model_ids": model_ids, "stdout": result.stdout}
    except Exception as exc:
        self.retry(exc=exc, countdown=120, max_retries=2)
