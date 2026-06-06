#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ENV_FILE="$ROOT_DIR/.env"
BACKUP_DIR="$ROOT_DIR/backups"
RESTORE_DB="emi_restore_test"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.prod.yml}"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

if [ -z "${MYSQL_ROOT_PASSWORD:-}" ]; then
  echo "MYSQL_ROOT_PASSWORD is required to restore backups"
  exit 1
fi

LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | head -n 1 || true)
if [ -z "$LATEST_BACKUP" ]; then
  echo "No backup file found in $BACKUP_DIR"
  exit 1
fi

cleanup() {
  docker compose -f "$COMPOSE_FILE" exec -T db sh -c "mysql -uroot -p\"$MYSQL_ROOT_PASSWORD\" -e \"DROP DATABASE IF EXISTS $RESTORE_DB\""
}
trap cleanup EXIT

docker compose -f "$COMPOSE_FILE" exec -T db sh -c "mysql -uroot -p\"$MYSQL_ROOT_PASSWORD\" -e \"DROP DATABASE IF EXISTS $RESTORE_DB; CREATE DATABASE $RESTORE_DB\""

gunzip -c "$LATEST_BACKUP" | docker compose -f "$COMPOSE_FILE" exec -T db sh -c "mysql -uroot -p\"$MYSQL_ROOT_PASSWORD\" $RESTORE_DB"

docker compose -f "$COMPOSE_FILE" exec -T db sh -c "mysql -uroot -p\"$MYSQL_ROOT_PASSWORD\" -N -e \"USE $RESTORE_DB; SELECT COUNT(*) FROM papers;\"" >/dev/null

echo "Backup restore test passed"
