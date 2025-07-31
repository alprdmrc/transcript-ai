# app/celery_client.py
from celery import Celery
from app.settings import settings

celery_app = Celery(
    "whisperx-transcription",
    broker=str(settings.CELERY_BROKER_URL),
    backend=str(settings.CELERY_RESULT_BACKEND),
)

# Client-side config (no need to include tasks in the API)
celery_app.conf.update(
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    enable_utc=True,
)