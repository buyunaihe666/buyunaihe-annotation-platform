from __future__ import annotations

import io
import uuid

from minio import Minio
from minio.error import S3Error

from . import config

_client: Minio | None = None


def get_minio() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=config.MINIO_SECURE,
        )
    return _client


def ensure_buckets() -> None:
    try:
        client = get_minio()
        for bucket in config.MINIO_BUCKETS:
            try:
                client.bucket_exists(bucket)
            except S3Error:
                pass
            if not _bucket_exists_safe(client, bucket):
                client.make_bucket(bucket)
            try:
                from minio.commonconfig import PublicAccess

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
        print(f"[minio] ensure_buckets failed: {e}")


def _bucket_exists_safe(client: Minio, bucket: str) -> bool:
    try:
        return client.bucket_exists(bucket)
    except S3Error:
        return False
    except Exception:
        return False


def upload_bytes(bucket: str, data: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
    client = get_minio()
    object_name = f"{bucket}/{uuid.uuid4().hex}/{filename}"
    client.put_object(bucket, object_name, io.BytesIO(data), len(data), content_type=content_type)
    return object_name


def public_url(bucket: str, object_name: str) -> str:
    endpoint = config.LABELHUB_MINIO_PUBLIC_URL.rstrip("/")
    return f"{endpoint}/{bucket}/{object_name}"


def presigned_get(bucket: str, object_name: str) -> str:
    client = get_minio()
    try:
        from datetime import timedelta

        return client.presigned_get_object(bucket, object_name, expires=timedelta(hours=2))
    except Exception:
        return public_url(bucket, object_name)


def download_bytes(bucket: str, object_name: str) -> bytes:
    client = get_minio()
    resp = client.get_object(bucket, object_name)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()