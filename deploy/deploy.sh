#!/bin/sh
# Buyunaihe one-click deploy (Linux / macOS)
# Usage: sh deploy/deploy.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/docker.env"

if [ ! -f "$ENV_FILE" ]; then
  if [ -f "$SCRIPT_DIR/docker.env.example" ]; then
    cp "$SCRIPT_DIR/docker.env.example" "$ENV_FILE"
    echo "[deploy] Created deploy/docker.env from template. Edit it if needed."
  else
    echo "[deploy] Missing deploy/docker.env.example" >&2
    exit 1
  fi
fi

echo "[deploy] Building images ..."
docker compose --env-file "$ENV_FILE" build

echo "[deploy] Running agent database migration (one-shot) ..."
docker compose --profile migrate --env-file "$ENV_FILE" run --rm agent-migrate || \
  echo "[deploy] agent-migrate returned non-zero (tables may already exist; continuing)"

echo "[deploy] Starting all services ..."
docker compose --env-file "$ENV_FILE" up -d

echo ""
echo "[deploy] Done."
echo "  Frontend:        http://localhost:${FRONTEND_HOST_PORT:-8088}"
echo "  Backend API:     http://localhost:8080"
echo "  Agent Web:       http://localhost:5001"
echo "  RabbitMQ admin:  http://localhost:15672"
echo "  MinIO console:   http://localhost:9001"
echo "  MySQL (host):    localhost:${MYSQL_HOST_PORT:-3307}"
echo "  Default login:   admin / 123456"
