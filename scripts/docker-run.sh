#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-ghcr.io/tsaitang404/geneticgrid:v0.1.0}"
CONTAINER_NAME="${CONTAINER_NAME:-geneticgrid}"
ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/.env}"
DB_FILE="${DB_FILE:-$PROJECT_ROOT/db.sqlite3}"
PORT="${PORT:-8000}"

is_truthy() {
  local value="${1:-}"
  [[ "$value" == "true" || "$value" == "1" || "$value" == "yes" || "$value" == "on" ]]
}

is_local_proxy_host() {
  local value="${1:-}"
  [[ "$value" == "127.0.0.1" || "$value" == "localhost" ]]
}

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
PROXY_CONTAINER_NETWORK_MODE="${PROXY_CONTAINER_NETWORK_MODE:-auto}"

NETWORK_ARGS=()
EXTRA_ENV_ARGS=()
EXTRA_HOST_ARG=()

AUTO_USE_HOST_NETWORK=false
if [[ "$PROXY_CONTAINER_NETWORK_MODE" == "auto" ]] \
  && is_truthy "$PROXY_ENABLED" \
  && [[ "$(uname -s)" == "Linux" ]] \
  && (is_local_proxy_host "${HTTP_PROXY_HOST:-}" || is_local_proxy_host "${SOCKS5_PROXY_HOST:-}"); then
  AUTO_USE_HOST_NETWORK=true
fi

if [[ "$PROXY_CONTAINER_NETWORK_MODE" == "host" || "$AUTO_USE_HOST_NETWORK" == "true" ]]; then
  NETWORK_ARGS=(--network host)
  EXTRA_ENV_ARGS=(-e PROXY_CONTAINER_AUTO_HOST=false)
else
  NETWORK_ARGS=(-p "${PORT}:8000")
  if is_truthy "$PROXY_CONTAINER_AUTO_HOST"; then
    EXTRA_HOST_ARG=(--add-host="${PROXY_CONTAINER_HOST}:host-gateway")
  fi
fi

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$CONTAINER_NAME" \
  "${NETWORK_ARGS[@]}" \
  --env-file "$ENV_FILE" \
  "${EXTRA_ENV_ARGS[@]}" \
  "${EXTRA_HOST_ARG[@]}" \
  -v "$ENV_FILE:/app/.env:ro" \
  -v "$DB_FILE:/app/db.sqlite3" \
  "$IMAGE"

echo "[docker-run] started ${CONTAINER_NAME} with image ${IMAGE}"
echo "[docker-run] env-file: ${ENV_FILE}"
if [[ ${#NETWORK_ARGS[@]} -gt 0 && "${NETWORK_ARGS[0]}" == "--network" ]]; then
  echo "[docker-run] network mode: host"
  echo "[docker-run] localhost proxy will be used directly from container"
else
  echo "[docker-run] network mode: bridge"
  echo "[docker-run] proxy auto host: ${PROXY_CONTAINER_AUTO_HOST}, host alias: ${PROXY_CONTAINER_HOST}"
fi
echo "[docker-run] visit: http://127.0.0.1:${PORT}"
