from datetime import datetime
from typing import Any
from app.db import SessionLocal
from app.models import TranscriptionJob, JobStatus

def update_job(job_id: str, **fields: Any) -> None:
    with SessionLocal() as db:
        job = db.get(TranscriptionJob, job_id)
        if not job:
            return
        for k, v in fields.items():
            setattr(job, k, v)
        # optional: bump a last_update_at column if you have one
        db.commit()