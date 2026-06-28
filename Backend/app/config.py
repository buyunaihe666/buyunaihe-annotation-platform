from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# DATABASE_URL takes precedence and supports any SQLAlchemy URL, e.g.:
#   sqlite:///./labelhub.db            (local dev, default)
#   postgresql+psycopg2://user:pw@host:5432/labelhub
#   mysql+pymysql://user:pw@host:3306/labelhub
DATABASE_URL = os.environ.get("DATABASE_URL", "")

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "labelhub")

# PostgreSQL (preferred when reusing an existing PG server)
PG_HOST = os.environ.get("PG_HOST", os.environ.get("MYSQL_HOST", "localhost"))
PG_PORT = os.environ.get("PG_PORT", "5432")
PG_USER = os.environ.get("PG_USER", os.environ.get("MYSQL_USER", "postgres"))
PG_PASSWORD = os.environ.get("PG_PASSWORD", os.environ.get("MYSQL_PASSWORD", ""))
PG_DATABASE = os.environ.get("PG_DATABASE", os.environ.get("MYSQL_DATABASE", "labelhub"))

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

# ---------------------------------------------------------------------------
# RabbitMQ (optional — publish gracefully degrades when unavailable)
# ---------------------------------------------------------------------------
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.environ.get("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "guest")
RABBITMQ_EXCHANGE = "labelhub"
RABBITMQ_ROUTING_KEY = "ai_audit"
RABBITMQ_QUEUE = "ai_audit"

# ---------------------------------------------------------------------------
# Object storage — MinIO or local filesystem fallback
# ---------------------------------------------------------------------------
# STORAGE_BACKEND = "minio" (default when MinIO reachable) | "local"
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "auto")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"
LABELHUB_MINIO_PUBLIC_URL = os.environ.get(
    "LABELHUB_MINIO_PUBLIC_URL", "/local-files"
)
MINIO_BUCKETS = ["annotation", "dataset", "export", "template"]

# Local filesystem storage (used when MinIO is unavailable)
LOCAL_STORAGE_DIR = os.environ.get("LOCAL_STORAGE_DIR", os.path.join(os.getcwd(), ".local_files"))

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
# Dev fallback secret so the backend can boot locally without env config.
JWT_SECRET = os.environ.get("JWT_SECRET", "buyunaihe-dev-secret-change-in-production")
JWT_ALG = "HS256"
JWT_TTL_HOURS = 24

APP_ADMIN_PASSWORD = os.environ.get("APP_ADMIN_PASSWORD", "admin")

# ---------------------------------------------------------------------------
# AI Agent (optional — calls degrade gracefully when unreachable)
# ---------------------------------------------------------------------------
AGENT_WEB_URL = os.environ.get("AGENT_WEB_URL", "http://localhost:5001")


def database_url() -> str:
    """Return the SQLAlchemy database URL.

    Priority:
      1. Explicit DATABASE_URL env var
      2. PostgreSQL connection (when PG_PASSWORD is set, i.e. Docker/prod)
      3. Local SQLite file (zero-config local dev)
    """
    if DATABASE_URL:
        return DATABASE_URL
    if PG_PASSWORD:
        return (
            f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}"
            f"/{PG_DATABASE}"
        )
    # Zero-config local dev: SQLite
    return "sqlite:///./labelhub.db"


# Backward-compatible alias
def mysql_url() -> str:
    return database_url()
