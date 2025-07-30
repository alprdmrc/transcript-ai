from fastapi import FastAPI
from app.settings import settings
from app.routes.transcriptions import router as transcriptions_router

app = FastAPI(title=settings.APP_NAME)

@app.get("/")
def root():
    return {"Uruk seni selamlıyor"}

@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok"}

# Versioned API
app.include_router(transcriptions_router, prefix=settings.API_PREFIX)
