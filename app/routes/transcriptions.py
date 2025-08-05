from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from pydantic import BaseModel, HttpUrl
import os
import uuid
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
    raise ValueError("AZURE_STORAGE_CONNECTION_STRING ve AZURE_STORAGE_CONTAINER_NAME ayarlanmamış.")
blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)

@router.post("/uploadfile/", tags=["File Upload"])
async def upload_file(file: UploadFile = File(...)):
    """
    This endpoint saves the file to Azure Blob Storage.
    """
    try:
        print("gelen file",file)
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

        return {
            "message": f"'{file.filename}' saved as '{unique_filename}' successfully.",
            "url": blob_url
        }
    
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e}")
    



class TranscriptionRequest(BaseModel):
    audio_url: HttpUrl
    metadata: dict | None = None


@router.post("/transcriptions")
def create_transcription(req: TranscriptionRequest, token: str = Depends(get_current_user)):
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
def get_transcription_status(job_id: str, token: str = Depends(get_current_user)):
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
