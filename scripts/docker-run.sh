#!/usr/bin/env bash
# GeneticGrid Docker/Compose 启动脚本
# 用法:
#   ./scripts/docker-run.sh              # 直接运行容器（需指定 IMAGE）
#   ./scripts/docker-run.sh compose      # 使用 docker-compose / podman-compose 启动
#   ./scripts/docker-run.sh compose:up   # 同上
#   ./scripts/docker-run.sh compose:down # 停止并移除
#   ./scripts/docker-run.sh compose:logs # 查看日志
#   ./scripts/docker-run.sh compose:rebuild  # 强制重建并启动
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${1:-run}"
COMPOSE_CMD="${COMPOSE_CMD:-podman-compose}"
PODMAN_SOCKET="/run/user/1000/podman/podman.sock"

# ---------------------------------------------------------------------------
# Compose 模式
# ---------------------------------------------------------------------------
if [[ "$ACTION" =~ ^compose ]]; then
  COMPOSE_ACTION="${2:-up}"

  # 自动检测 podman socket 并设置 DOCKER_HOST
  if [[ "$COMPOSE_CMD" == "podman-compose" && -S "$PODMAN_SOCKET" ]]; then
    export DOCKER_HOST="unix://$PODMAN_SOCKET"
    echo "[compose] Using Podman socket: $DOCKER_HOST"
  fi

  cd "$PROJECT_ROOT"

  case "$COMPOSE_ACTION" in
    up|start)
      echo "[compose] Starting GeneticGrid via ${COMPOSE_CMD} ..."
      $COMPOSE_CMD up -d
      echo "[compose] Visit http://127.0.0.1:8000"
      ;;
    down|stop)
      echo "[compose] Stopping GeneticGrid ..."
      $COMPOSE_CMD down
      ;;
    logs)
      $COMPOSE_CMD logs -f
      ;;
    rebuild)
      echo "[compose] Rebuilding and starting GeneticGrid ..."
      $COMPOSE_CMD up -d --build
      echo "[compose] Rebuild complete. Visit http://127.0.0.1:8000"
      ;;
    *)
      echo "[compose] Unknown action: $COMPOSE_ACTION"
      echo "Usage: $0 compose [up|down|logs|rebuild]"
      exit 1
      ;;
  esac
  exit 0
fi

# ---------------------------------------------------------------------------
# 原始 docker run 模式（向下兼容）
# ---------------------------------------------------------------------------
IMAGE="${IMAGE:-ghcr.io/tsaitang404/geneticgrid:v0.2.2}"
CONTAINER_NAME="${CONTAINER_NAME:-geneticgrid}"
ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/.env}"
DATA_DIR="${DATA_DIR:-$PROJECT_ROOT/data}"
CONTAINER_DATA_DIR="${CONTAINER_DATA_DIR:-/app/data}"
DB_FILE="${DB_FILE:-$DATA_DIR/db.sqlite3}"
DB_PATH="${DB_PATH:-$CONTAINER_DATA_DIR/db.sqlite3}"
PORT="${PORT:-8000}"
APP_ENV_VARS=(
  DJANGO_SECRET_KEY
  ALLOWED_HOSTS
  DB_PATH
  REALTIME_INGESTION_AUTO_START
  REALTIME_INGESTION_STREAMS
  REDIS_CACHE_ENABLED
  REDIS_CACHE_URL
  REDIS_CACHE_TTL_SECONDS
  REDIS_CACHE_MAX_ENTRIES
)

append_env_arg_if_set() {
  local name="$1"
  if [[ -n "${!name+x}" ]]; then
    PASS_THROUGH_ENV_ARGS+=("-e" "$name=${!name}")
  fi
}

mkdir -p "$DATA_DIR"

if [[ ! -f "$DB_FILE" ]]; then
  touch "$DB_FILE"
fi

ENV_FILE_ARGS=()
ENV_FILE_MOUNT_ARGS=()
PASS_THROUGH_ENV_ARGS=()

if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  ENV_FILE_ARGS=(--env-file "$ENV_FILE")
  ENV_FILE_MOUNT_ARGS=(-v "$ENV_FILE:/app/.env:ro")
fi

for env_name in "${APP_ENV_VARS[@]}"; do
  append_env_arg_if_set "$env_name"
done

NETWORK_ARGS=()
EXTRA_ENV_ARGS=()
EXTRA_HOST_ARG=()
NETWORK_ARGS=(-p "${PORT}:8000")
EXTRA_HOST_ARG=(--add-host=host.docker.internal:host-gateway)

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$CONTAINER_NAME" \
  "${NETWORK_ARGS[@]}" \
  "${ENV_FILE_ARGS[@]}" \
  "${PASS_THROUGH_ENV_ARGS[@]}" \
  -e "DB_PATH=$DB_PATH" \
  "${EXTRA_ENV_ARGS[@]}" \
  "${EXTRA_HOST_ARG[@]}" \
  "${ENV_FILE_MOUNT_ARGS[@]}" \
  -v "$DATA_DIR:$CONTAINER_DATA_DIR" \
  "$IMAGE"

echo "[docker-run] started ${CONTAINER_NAME} with image ${IMAGE}"
echo "[docker-run] data-dir: ${DATA_DIR} -> ${CONTAINER_DATA_DIR}"
echo "[docker-run] db-path: ${DB_PATH}"
if [[ ${#ENV_FILE_ARGS[@]} -gt 0 ]]; then
  echo "[docker-run] env-file: ${ENV_FILE}"
else
  echo "[docker-run] env-file: disabled, using shell/docker environment variables or built-in defaults"
fi
echo "[docker-run] network mode: bridge"
echo "[docker-run] host alias injected: host.docker.internal -> host-gateway"
echo "[docker-run] visit: http://127.0.0.1:${PORT}"
