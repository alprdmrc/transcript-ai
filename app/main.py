from fastapi import FastAPI
from app.db import Base, engine
from app.settings import settings
from app.routes.transcriptions import router as transcriptions_router
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ----- startup -----
    # Dev-only: create tables if they do not exist.
    # In prod, prefer running Alembic migrations instead of create_all.
    Base.metadata.create_all(bind=engine)

    yield

    # ----- shutdown -----
    # Dispose pooled DB connections so the process exits cleanly
    engine.dispose()

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

@app.get("/")
def root():
    return {"Uruk seni selamlıyor"}

@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok"}

# Versioned API
app.include_router(transcriptions_router, prefix=settings.API_PREFIX)
