#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ENV_FILE="$ROOT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

MYSQL_USER=${MYSQL_USER:-emi}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-emipass}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed or not in PATH"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is not installed or not in PATH"
  exit 1
fi

health=$(curl -s http://localhost:8000/health)
if [[ "$health" != *"ok"* ]]; then
  echo "Health check failed: $health"
  exit 1
fi

curl -s -I http://localhost:5173 | head -n 1 | grep -q "200" || { echo "Frontend not reachable"; exit 1; }
curl -s -I http://localhost:8000/docs | head -n 1 | grep -q "200" || { echo "API docs not reachable"; exit 1; }

docker exec emi_mysql mysqladmin ping -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" | grep -q "mysqld is alive" || { echo "MySQL not reachable"; exit 1; }

echo "Smoke test passed"
