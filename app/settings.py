from pydantic_settings import BaseSettings
from pydantic import AnyUrl

class Settings(BaseSettings):
    # FastAPI
    APP_NAME: str = "whisperx-transcription"
    API_PREFIX: str = "/v1"

    # Humanas BE
    MAIN_BACKEND_URL: str | None = None

    # Celery / Redis
    REDIS_URL: AnyUrl = "redis://localhost:6379/0"
    CELERY_BROKER_URL: AnyUrl | None = None
    CELERY_RESULT_BACKEND: AnyUrl | None = None

    # Security (MVP placeholders)
    AUTH_JWT_ISS: str | None = None
    AUTH_JWT_AUD: str | None = None
    AUTH_JWKS_URL: str | None = None

    # Database settings for MySQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_SCHEMA: str = "app"
    DB_USERNAME: str = "user"
    DB_PASSWORD: str = "password"

    # WhisperX config
    WHISPERX_DEVICE: str | None = None
    WHISPERX_MODEL_NAME: str | None = None  
    WHISPERX_COMPUTE_TYPE: str | None = None # "float16" on mps/cuda, "int8" on cpu ## "float32","float16","int8",...
    WHISPERX_ENABLE_ALIGNMENT: bool = True
    WHISPERX_ENABLE_DIARIZATION: bool = False  # pyannote is heavy; keep off for MVP
    HUGGINGFACE_TOKEN: str | None = None  

    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: str | None = None
    AZURE_CONTAINER_NAME: str | None = None

    class Config:
        env_file = ".env"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+mysqlconnector://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_SCHEMA}"
        )



settings = Settings()
# Default Celery endpoints to REDIS_URL if not set explicitly
if settings.CELERY_BROKER_URL is None:
    settings.CELERY_BROKER_URL = settings.REDIS_URL
if settings.CELERY_RESULT_BACKEND is None:
    settings.CELERY_RESULT_BACKEND = settings.REDIS_URL

# Detect device
# def default_device() -> str:
#     try:
#         import torch
#         if torch.backends.mps.is_available():
#             return "cuda"
#     except Exception:
#         pass
#     return "cpu"

# DEVICE = default_device()

# def _resolve_compute_type(device: str) -> str:
#     # float16 only makes sense on CUDA; use float32 on CPU
#     print("type to resolve", device)
#     return "float16" if device == "cuda" else "float32"

# COMPUTE_TYPE = _resolve_compute_type(DEVICE)