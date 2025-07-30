from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from worker.celery_app import celery_app
from celery.result import AsyncResult

from app.db import SessionLocal
from app.models import TranscriptionJob, JobStatus

router = APIRouter(tags=["transcriptions"])


class TranscriptionRequest(BaseModel):
    audio_url: HttpUrl
    metadata: dict | None = None


@router.post("/transcriptions")
def create_transcription(req: TranscriptionRequest):
    """
    MVP: enqueue a job and return Celery task_id as job_id.
    (Auth, SSRF allowlist, and idempotency will come next.)
    """
    async_res = celery_app.send_task(
        "worker.tasks.transcribe_task",
        kwargs={"audio_url": str(req.audio_url), "metadata": req.metadata or {}},
    )
    with SessionLocal() as db:
        db.add(TranscriptionJob(
            job_id=async_res.id,
            audio_url=str(req.audio_url),
            status=JobStatus.queued,
            request_metadata=req.metadata or {},
        ))
        db.commit()
    return {"job_id": async_res.id, "status": "queued"}


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict | None = None
    error: str | None = None


@router.get("/transcriptions/{job_id}", response_model=JobStatusResponse)
def get_transcription_status(job_id: str):
    res = AsyncResult(job_id, app=celery_app)
    state = res.state

    if state in ("PENDING", "RECEIVED"):
        return JobStatusResponse(job_id=job_id, status="queued")
    if state == "STARTED":
        return JobStatusResponse(job_id=job_id, status="running")
    if state == "SUCCESS":
        return JobStatusResponse(job_id=job_id, status="succeeded", result=res.result)
    if state == "FAILURE":
        # Avoid leaking internals—return a generic error string for now
        return JobStatusResponse(job_id=job_id, status="failed", error=str(res.info))

    # Catch-all for uncommon Celery states
    return JobStatusResponse(job_id=job_id, status=state.lower())
