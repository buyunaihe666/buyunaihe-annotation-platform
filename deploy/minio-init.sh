#!/bin/sh
set -e
echo "[minio-init] waiting for MinIO at http://minio:9000 ..."
until mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
  sleep 2
done
echo "[minio-init] connected, creating buckets ..."
for b in annotation dataset export template; do
  mc mb -p "local/$b" >/dev/null 2>&1 || true
  mc anonymous set download "local/$b" >/dev/null 2>&1 || true
  echo "[minio-init] bucket $b ready (anonymous download)"
done
echo "[minio-init] done"
