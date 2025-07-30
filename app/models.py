# app/models.py
from datetime import datetime
from sqlalchemy import String, Text, JSON, Float, Enum, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CheckConstraint
from app.db import Base
import enum

class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"

class TranscriptionJob(Base):
    __tablename__ = "transcription_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    audio_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Portable ENUM: native_enum=False -> becomes VARCHAR+CHECK on SQLite/MySQL
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, validate_strings=True),
        nullable=False,
        index=True,
        default=JobStatus.queued,
        server_default=text("'queued'")
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )
    enqueued_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)

    request_metadata: Mapped[dict | None] = mapped_column(JSON, default=None)
    language: Mapped[str | None] = mapped_column(String(16), default=None)
    duration_sec: Mapped[float | None] = mapped_column(Float, default=None)
    model_name: Mapped[str | None] = mapped_column(String(64), default=None)
    device: Mapped[str | None] = mapped_column(String(16), default=None)
    compute_type: Mapped[str | None] = mapped_column(String(32), default=None)

    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    transcript_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    result_blob_url: Mapped[str | None] = mapped_column(Text, default=None)
