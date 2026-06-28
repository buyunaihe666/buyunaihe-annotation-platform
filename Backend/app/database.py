from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from . import config

_url = config.database_url()
_connect_args = {}
if _url.startswith("sqlite"):
    # SQLite needs this for multi-thread FastAPI usage
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    _url,
    pool_pre_ping=not _url.startswith("sqlite"),
    pool_recycle=3600,
    future=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()