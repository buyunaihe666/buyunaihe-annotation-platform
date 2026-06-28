from __future__ import annotations

import io
import os
import uuid
import logging

from . import config

logger = logging.getLogger("buyunaihe.storage")

_client = None
# Resolved backend: "minio" or "local". Determined at startup by ensure_buckets().
_backend: str | None = None


def _resolve_backend() -> str:
    """Decide which storage backend to use.

    STORAGE_BACKEND env:
      - "local"  → always use local filesystem
      - "minio"  → always use MinIO
      - "auto"   → try MinIO; fall back to local if unreachable (default)
    """
    global _backend
    if _backend is not None:
        return _backend
    mode = (config.STORAGE_BACKEND or "auto").lower()
    if mode == "local":
        _backend = "local"
    elif mode == "minio":
        _backend = "minio"
    else:
        # auto: probe MinIO with a quick socket check (much faster than client retries)
        try:
            import socket

            host = config.MINIO_ENDPOINT.split(":")[0]
            port = int(config.MINIO_ENDPOINT.split(":")[1]) if ":" in config.MINIO_ENDPOINT else 9000
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.5)
            if s.connect_ex((host, port)) == 0:
                s.close()
                _backend = "minio"
                logger.info("[storage] MinIO reachable, using minio backend")
            else:
                s.close()
                logger.warning(f"[storage] MinIO not reachable at {host}:{port}, using local filesystem")
                _backend = "local"
        except Exception as e:
            logger.warning(f"[storage] MinIO probe failed ({e}), using local filesystem")
            _backend = "local"
    return _backend


def get_minio():
    global _client
    if _client is None:
        from minio import Minio

        _client = Minio(
            config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=config.MINIO_SECURE,
        )
    return _client


# ---------------------------------------------------------------------------
# Bucket / directory initialization
# ---------------------------------------------------------------------------
def ensure_buckets() -> None:
    backend = _resolve_backend()
    if backend == "local":
        os.makedirs(config.LOCAL_STORAGE_DIR, exist_ok=True)
        for bucket in config.MINIO_BUCKETS:
            os.makedirs(os.path.join(config.LOCAL_STORAGE_DIR, bucket), exist_ok=True)
        return
    # MinIO mode
    try:
        client = get_minio()
        for bucket in config.MINIO_BUCKETS:
            if not _bucket_exists_safe(client, bucket):
                client.make_bucket(bucket)
            try:
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket}/*"],
                        }
                    ],
                }
                import json

                client.set_bucket_policy(bucket, json.dumps(policy))
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"[storage] MinIO ensure_buckets failed: {e}, switching to local")
        global _backend
        _backend = "local"
        ensure_buckets()


def _bucket_exists_safe(client, bucket: str) -> bool:
    try:
        return client.bucket_exists(bucket)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Upload / download / URL
# ---------------------------------------------------------------------------
def upload_bytes(bucket: str, data: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
    """Upload bytes and return the object_name (storage key)."""
    object_name = f"{bucket}/{uuid.uuid4().hex}/{filename}"
    backend = _resolve_backend()
    if backend == "local":
        dest = os.path.join(config.LOCAL_STORAGE_DIR, object_name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        return object_name
    # MinIO
    client = get_minio()
    client.put_object(bucket, object_name, io.BytesIO(data), len(data), content_type=content_type)
    return object_name


def public_url(bucket: str, object_name: str) -> str:
    backend = _resolve_backend()
    if backend == "local":
        endpoint = config.LABELHUB_MINIO_PUBLIC_URL.rstrip("/")
        return f"{endpoint}/{object_name}"
    # MinIO: endpoint/{bucket}/{object_name}
    endpoint = config.LABELHUB_MINIO_PUBLIC_URL.rstrip("/")
    return f"{endpoint}/{bucket}/{object_name}"


def presigned_get(bucket: str, object_name: str) -> str:
    backend = _resolve_backend()
    if backend == "local":
        return public_url(bucket, object_name)
    try:
        from datetime import timedelta

        client = get_minio()
        return client.presigned_get_object(bucket, object_name, expires=timedelta(hours=2))
    except Exception:
        return public_url(bucket, object_name)


def download_bytes(bucket: str, object_name: str) -> bytes:
    backend = _resolve_backend()
    if backend == "local":
        path = os.path.join(config.LOCAL_STORAGE_DIR, object_name)
        with open(path, "rb") as f:
            return f.read()
    client = get_minio()
    resp = client.get_object(bucket, object_name)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


def local_file_path(object_name: str) -> str | None:
    """Return the absolute filesystem path for a local-storage object, or None."""
    if _resolve_backend() != "local":
        return None
    path = os.path.join(config.LOCAL_STORAGE_DIR, object_name)
    return path if os.path.isfile(path) else None
