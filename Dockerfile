FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git curl ca-certificates supervisor && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-api.txt requirements-worker.txt ./
RUN pip install -U pip && pip install -r requirements-api.txt && pip install -r requirements-worker.txt

COPY app/ app/
COPY worker/ worker/
COPY dbmigrations/ dbmigrations/
COPY alembic.ini alembic.ini
COPY deployment/docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 8080

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]