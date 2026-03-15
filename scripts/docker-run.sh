#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-ghcr.io/tsaitang404/geneticgrid:v0.1.0}"
CONTAINER_NAME="${CONTAINER_NAME:-geneticgrid}"
ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/.env}"
DB_FILE="${DB_FILE:-$PROJECT_ROOT/db.sqlite3}"
PORT="${PORT:-8000}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[docker-run] missing env file: $ENV_FILE" >&2
  exit 1
fi

if [[ ! -f "$DB_FILE" ]]; then
  touch "$DB_FILE"
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

PROXY_CONTAINER_AUTO_HOST="${PROXY_CONTAINER_AUTO_HOST:-true}"
PROXY_CONTAINER_HOST="${PROXY_CONTAINER_HOST:-host.docker.internal}"

EXTRA_HOST_ARG=()
if [[ "$PROXY_CONTAINER_AUTO_HOST" == "true" || "$PROXY_CONTAINER_AUTO_HOST" == "1" || "$PROXY_CONTAINER_AUTO_HOST" == "yes" ]]; then
  EXTRA_HOST_ARG=(--add-host="${PROXY_CONTAINER_HOST}:host-gateway")
fi

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$CONTAINER_NAME" \
  -p "${PORT}:8000" \
  --env-file "$ENV_FILE" \
  "${EXTRA_HOST_ARG[@]}" \
  -v "$ENV_FILE:/app/.env:ro" \
  -v "$DB_FILE:/app/db.sqlite3" \
  "$IMAGE"

echo "[docker-run] started ${CONTAINER_NAME} with image ${IMAGE}"
echo "[docker-run] env-file: ${ENV_FILE}"
echo "[docker-run] proxy auto host: ${PROXY_CONTAINER_AUTO_HOST}, host alias: ${PROXY_CONTAINER_HOST}"
echo "[docker-run] visit: http://127.0.0.1:${PORT}"
