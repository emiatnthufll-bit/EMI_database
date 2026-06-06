#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ENV_FILE="$ROOT_DIR/.env"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.prod.yml}"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

BACKUP_DIR="$ROOT_DIR/backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y-%m-%d_%H%M")
FILENAME="emi_db_${TIMESTAMP}.sql.gz"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed or not in PATH"
  exit 1
fi

docker compose -f "$COMPOSE_FILE" exec -T db sh -c 'mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' | gzip > "$BACKUP_DIR/$FILENAME"

echo "Backup saved to $BACKUP_DIR/$FILENAME"
