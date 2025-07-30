# app/db.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool
from app.settings import settings

class Base(DeclarativeBase):
    pass

def _make_engine():
    url = settings.DATABASE_URL
    is_sqlite = url.startswith("sqlite:")
    if is_sqlite:
        # SQLite: single-file DB for local dev; enable WAL & foreign keys
        engine = create_engine(
            url,
            future=True,
            poolclass=NullPool,  # avoid locks in multi-process dev
            connect_args={"check_same_thread": False},  # needed for Uvicorn+Celery in dev
        )
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
        return engine
    else:
        # MySQL in Azure
        return create_engine(
            url,
            future=True,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            pool_recycle=1800,                     # recycle every 30 min
            connect_args={"connection_timeout": 10}  # fast fail
        )

engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
