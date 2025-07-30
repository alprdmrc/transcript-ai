from pathlib import Path
from celery import shared_task
from app.downloader import download_to_tmp
from app.audio import normalize_wav
from app.engine_whisperx import transcribe_with_whisperx

@shared_task(name="worker.tasks.transcribe_task", bind=True)
def transcribe_task(self, audio_url: str, metadata: dict):
    job_id = self.request.id

    # 1) Download (must be a direct file URL — SAS/presigned — not an HTML page)
    self.update_state(state="STARTED", meta={"phase": "download"})
    src = download_to_tmp(audio_url, job_id)

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
    return result