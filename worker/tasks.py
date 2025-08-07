from datetime import datetime
from pathlib import Path
from celery import shared_task
from app.downloader import download_to_tmp
from app.audio import normalize_wav
from app.engine_whisperx import transcribe_with_whisperx
from worker.tasks_helpers import update_job
from app.models import JobStatus

@shared_task(name="worker.tasks.transcribe_task", bind=True)
def transcribe_task(self, audio_url: str, metadata: dict):
    job_id = self.request.id

    # mark running
    update_job(job_id, status=JobStatus.running, started_at=datetime.now(datetime.timezone.utc))
    try:
        # 1) Download
        self.update_state(state="STARTED", meta={"phase": "download"})
        src = download_to_tmp(audio_url, job_id)
        update_job(job_id, error_message=None)  # clear any stale error, optional

        # 2) Normalize (optional but safer for edge formats)
        self.update_state(state="STARTED", meta={"phase": "normalize"})
        norm = Path("data/tmp") / f"{job_id}.wav"
        try:
            audio_path = normalize_wav(src, norm)
        except Exception:
            audio_path = src  # fallback

        # 3) WhisperX
        self.update_state(state="STARTED", meta={"phase": "transcribe"})
        result = transcribe_with_whisperx(str(audio_path))

        # 4) Return contract
        result["request_metadata"] = metadata or {}
        result["source"] = {"audio_url": audio_url}
        last_segment = result["segments"][-1]
        total_duration_from_segments = last_segment["end"]
        update_job(
            job_id,
            status=JobStatus.succeeded,
            finished_at=datetime.now(datetime.timezone.utc),
            language=result.get("language"),
            duration_sec=total_duration_from_segments,
            model_name=result.get("model").get("name"),
            device=result.get("model").get("device"),
            compute_type=result.get("model").get("compute_type"),
            transcript_json=result,
            error_message=None,
        )
        return result
    except Exception as e:
        # failure
        update_job(
            job_id,
            status=JobStatus.failed,
            finished_at=datetime.now(datetime.timezone.utc),
            error_message=str(e),
        )
        raise