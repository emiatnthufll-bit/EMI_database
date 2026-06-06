#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or not in PATH"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is not installed or not in PATH"
  exit 1
fi

echo "[1/8] Starting Docker services..."
cd "$ROOT_DIR"
docker compose up -d

echo "[2/8] Waiting for API health check..."
health_ok=0
for i in $(seq 1 30); do
  if curl -s http://localhost:8000/health | grep -q '"ok"'; then
    health_ok=1
    break
  fi
  sleep 2
  echo "Waiting for API... ($i/30)"
done
if [ "$health_ok" -ne 1 ]; then
  echo "API health check failed"
  exit 1
fi

echo "[3/8] Running backend tests..."
cd "$ROOT_DIR/backend"
pytest

cd "$ROOT_DIR"

echo "[4/8] Running smoke test..."
bash scripts/test_smoke.sh

echo "[5/8] Running backup..."
bash scripts/backup_mysql.sh

echo "[6/8] Running backup restore validation..."
bash scripts/test_restore_backup.sh

echo "[7/8] Running production config check..."
python scripts/check_prod_config.py

echo "[8/8] All checks passed"
