from celery import Celery
from app.settings import settings

celery_app = Celery(
    "whisperx-transcription",
    broker=str(settings.CELERY_BROKER_URL),
    backend=str(settings.CELERY_RESULT_BACKEND),
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    result_expires=3600,  # 1 hour
    worker_prefetch_multiplier=1,
    timezone="UTC",
    enable_utc=True,
    include=["worker.tasks"],
)
