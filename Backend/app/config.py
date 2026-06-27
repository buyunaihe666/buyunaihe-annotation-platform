from __future__ import annotations

import os


def _default(val, fallback):
    return val if val is not None and val != "" else fallback


MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "labelhub")

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.environ.get("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "guest")

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"
LABELHUB_MINIO_PUBLIC_URL = os.environ.get(
    "LABELHUB_MINIO_PUBLIC_URL", "http://localhost:9000"
)

JWT_SECRET = os.environ.get("JWT_SECRET", "buyunaihe-dev-secret-change-me")
JWT_ALG = "HS256"
JWT_TTL_HOURS = 24

AGENT_WEB_URL = os.environ.get("AGENT_WEB_URL", "http://localhost:5001")

RABBITMQ_EXCHANGE = "labelhub"
RABBITMQ_ROUTING_KEY = "ai_audit"
RABBITMQ_QUEUE = "ai_audit"

MINIO_BUCKETS = ["annotation", "dataset", "export", "template"]


def mysql_url() -> str:
    return (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}"
        f"/{MYSQL_DATABASE}?charset=utf8mb4"
    )