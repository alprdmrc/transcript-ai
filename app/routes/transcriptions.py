from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from pydantic import BaseModel, HttpUrl
import os
import uuid
from datetime import datetime
# from worker.celery_app import celery_app
from app.celery_client import celery_app
from celery.result import AsyncResult

from app.db import SessionLocal
from app.models import TranscriptionJob, JobStatus
from app.permissions import get_current_user
from app.settings import settings
from azure.storage.blob import BlobServiceClient

router = APIRouter(tags=["transcriptions"])

azure_connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
azure_container_name = settings.AZURE_CONTAINER_NAME

if not azure_connection_string or not azure_container_name:
    raise ValueError("AZURE_STORAGE_CONNECTION_STRING and AZURE_CONTAINER_NAME are not set.")
blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)

@router.post("/uploadfile/", tags=["File Upload"])
async def upload_file(file: UploadFile = File(...), user_info: dict = Depends(get_current_user)):
    """
    This endpoint saves the file to Azure Blob Storage.
    """
    try:
        print("Processing file:",file)
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        # Get Container Client
        container_client = blob_service_client.get_container_client(azure_container_name)
        
        # Blob Client
        blob_client = container_client.get_blob_client(unique_filename)

        # Read file contents
        contents = await file.read()
        
        # Upload file to Azure Blob Storage
        blob_client.upload_blob(contents, overwrite=True)

        # Get blob URL
        blob_url = blob_client.url

        # Automatically create transcription job
        async_res = celery_app.send_task(
            "worker.tasks.transcribe_task",
            kwargs={"audio_url": blob_url, "metadata": {"original_filename": file.filename}},
        )

        # Save job to database
        with SessionLocal() as db:
            db.add(TranscriptionJob(
                job_id=async_res.id,
                audio_url=blob_url,
                status=JobStatus.queued,
                request_metadata={"original_filename": file.filename},
                user_info=user_info,
            ))
            db.commit()

        return {
            "message": f"'{file.filename}' uploaded and transcription job started successfully.",
            "url": blob_url,
            "job_id": async_res.id,
            "status": "queued"
        }
    
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e}")
    
class TranscriptionRequest(BaseModel):
    audio_url: HttpUrl
    metadata: dict | None = None

@router.post("/transcriptions")
def create_transcription(req: TranscriptionRequest, user_info: dict = Depends(get_current_user)):
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
            user_info=user_info,
        ))
        db.commit()
    return {"job_id": async_res.id, "status": "queued"}

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict | None = None
    error: str | None = None

@router.get("/transcriptions/{job_id}", response_model=JobStatusResponse)
def get_transcription_status(job_id: str, user_info: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        job = db.query(TranscriptionJob).filter(TranscriptionJob.job_id == job_id).first()
        if job and job.status in [JobStatus.canceled, JobStatus.failed, JobStatus.succeeded]:
            return JobStatusResponse(job_id=job_id, status=job.status.value)

    res = AsyncResult(job_id, app=celery_app)
    state = res.state

    if state == "REVOKED":
        return JobStatusResponse(job_id=job_id, status="canceled")
    if state in ("PENDING", "RECEIVED"):
        return JobStatusResponse(job_id=job_id, status="queued")
    if state == "STARTED":
        return JobStatusResponse(job_id=job_id, status="running")
    if state == "SUCCESS":
        return JobStatusResponse(job_id=job_id, status="succeeded", result=res.result)
    if state == "FAILURE":
        return JobStatusResponse(job_id=job_id, status="failed", error=str(res.info))

    return JobStatusResponse(job_id=job_id, status=state.lower())

class JobsListResponse(BaseModel):
    job_id: str
    status: str
    result: dict | None = None
    audio_url: str | None = None
    error: str | None = None
    created_at: datetime
    enqueued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    request_metadata: dict | None = None
    language: str | None = None
    duration_sec: float | None = None
    model_name: str | None = None
    device: str | None = None
    compute_type: str | None = None
    user_info: dict | None = None
    transcript_json: dict | None = None
    result_blob_url: str | None = None

# get all transctiptions with all transcription data fields
@router.get("/transcriptions", response_model=list[JobsListResponse])
def get_all_transcriptions(user_info: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        # sort jobs as created date desc
        jobs = db.query(TranscriptionJob).order_by(TranscriptionJob.created_at.desc()).all()
        return [JobsListResponse(job_id=job.job_id, audio_url=job.audio_url, status=job.status.value, result=job.transcript_json, error=job.error_message, created_at=job.created_at, enqueued_at=job.enqueued_at, started_at=job.started_at, finished_at=job.finished_at, request_metadata=job.request_metadata, language=job.language, duration_sec=job.duration_sec, model_name=job.model_name, device=job.device, compute_type=job.compute_type, user_info=job.user_info, transcript_json=job.transcript_json, result_blob_url=job.result_blob_url) for job in jobs]

# @router.post("/transcriptions/{job_id}/cancel", response_model=dict)
# def cancel_transcription(job_id: str):
#     """
#     Cancel a transcription job by its ID.
#     Only jobs with status 'queued' or 'running' can be canceled.
#     """
#     with SessionLocal() as db:
#         # Get the job from the database
#         job = db.query(TranscriptionJob).filter(TranscriptionJob.job_id == job_id).first()
        
#         if not job:
#             raise HTTPException(status_code=404, detail="Job not found")
            
#         if job.status in [JobStatus.succeeded, JobStatus.failed, JobStatus.canceled]:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Cannot cancel job with status '{job.status}'"
#             )
        
#         # Update job status to canceled
#         job.status = JobStatus.canceled
#         job.finished_at = datetime.utcnow()
        
#         # Try to revoke the Celery task
#         celery_app.control.revoke(job_id, terminate=True, signal='SIGTERM')
            
#         db.commit()
    
#     return {"status": "success", "message": f"Job {job_id} has been canceled"}
