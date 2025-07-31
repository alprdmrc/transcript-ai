# syntax=docker/dockerfile:1.7

############################
# Base stage (shared bits) #
############################
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# OS deps shared by both images
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement files up front to leverage Docker layer caching
COPY requirements-api.txt requirements-worker.txt ./
# If you are using constraints, uncomment next line:
# COPY constraints.txt .

########################
# API target (lean)    #
########################
FROM base AS api

# Install API deps only (no Torch/WhisperX here!)
# If using constraints: add `-c constraints.txt`
RUN pip install -U pip && pip install -r requirements-api.txt

# Copy only what API needs
COPY app/ app/
COPY dbmigrations/ dbmigrations/
COPY alembic.ini alembic.ini

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host","0.0.0.0","--port","8080"]

########################
# Worker target (ML)   #
########################
FROM base AS worker

# Install Worker deps (Torch/WhisperX, Celery, etc.)
# If using constraints: add `-c constraints.txt`
RUN pip install -U pip && pip install -r requirements-worker.txt

# Copy worker runtime
COPY app/ app/
COPY worker/ worker/

# Logs unbuffered + default concurrency (override via env)
ENV PYTHONUNBUFFERED=1 \
    CELERYD_CONCURRENCY=1

CMD ["bash","-lc","celery -A worker.celery_app.celery_app worker -l INFO --concurrency=${CELERYD_CONCURRENCY}"]
