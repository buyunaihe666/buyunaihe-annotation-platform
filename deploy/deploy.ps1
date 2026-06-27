# Buyunaihe one-click deploy (Windows PowerShell)
# Usage: .\deploy\deploy.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $PSScriptRoot "docker.env"

if (-not (Test-Path -LiteralPath $envFile)) {
    $example = Join-Path $PSScriptRoot "docker.env.example"
    if (Test-Path -LiteralPath $example) {
        Copy-Item -LiteralPath $example -Destination $envFile
        Write-Host "[deploy] Created deploy/docker.env from template. Edit it if needed." -ForegroundColor Yellow
    } else {
        Write-Error "Missing deploy/docker.env.example"
        exit 1
    }
}

Write-Host "[deploy] Building images ..." -ForegroundColor Cyan
docker compose --env-file $envFile build
if (-not $?) { Write-Error "build failed"; exit 1 }

Write-Host "[deploy] Running agent database migration (one-shot) ..." -ForegroundColor Cyan
docker compose --profile migrate --env-file $envFile run --rm agent-migrate
if (-not $?) { Write-Host "[deploy] agent-migrate returned non-zero (tables may already exist; continuing)" -ForegroundColor Yellow }

Write-Host "[deploy] Starting all services ..." -ForegroundColor Cyan
docker compose --env-file $envFile up -d
if (-not $?) { Write-Error "up failed"; exit 1 }

Write-Host ""
Write-Host "[deploy] Done." -ForegroundColor Green
Write-Host "  Frontend:        http://localhost:$env:FRONTEND_HOST_PORT"
Write-Host "  Backend API:     http://localhost:8080"
Write-Host "  Agent Web:       http://localhost:5001"
Write-Host "  RabbitMQ admin:  http://localhost:15672"
Write-Host "  MinIO console:   http://localhost:9001"
Write-Host "  MySQL (host):    localhost:$env:MYSQL_HOST_PORT  (user=$env:MYSQL_USER)"
Write-Host "  Default login:   admin / 123456"
