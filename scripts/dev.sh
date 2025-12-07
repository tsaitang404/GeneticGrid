#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYENV_VERSION_FILE="$PROJECT_ROOT/.python-version"
NVM_VERSION_FILE="$PROJECT_ROOT/.nvmrc"
FALLBACK_NODE_VERSION="20.17.0"
DJANGO_ADDR="${DJANGO_ADDR:-127.0.0.1:8000}"
VITE_HOST="${VITE_HOST:-0.0.0.0}"

log() {
  printf '[dev] %s\n' "$*"
}

PYTHON_CMD="python"
if command -v pyenv >/dev/null 2>&1; then
  log "Initializing pyenv"
  eval "$(pyenv init -)"
  if [[ -f "$PYENV_VERSION_FILE" ]]; then
    PYTHON_VERSION="$(tr -d ' \n' < "$PYENV_VERSION_FILE")"
    if [[ -n "$PYTHON_VERSION" ]]; then
      log "Using Python ${PYTHON_VERSION} (pyenv)"
      pyenv install -s "$PYTHON_VERSION"
      if ! pyenv shell "$PYTHON_VERSION" >/dev/null 2>&1; then
        echo "[dev] Failed to activate pyenv Python ${PYTHON_VERSION}" >&2
        exit 1
      fi
      PYTHON_CMD="$(pyenv which python)"
    fi
  fi
else
  log "pyenv not detected, falling back to system Python"
fi

if [[ -z "$PYTHON_CMD" || ! -x "$PYTHON_CMD" ]]; then
  if ! command -v python >/dev/null 2>&1; then
    echo "[dev] python command not found. Ensure pyenv/system python is available." >&2
    exit 1
  fi
  PYTHON_CMD="$(command -v python)"
fi

if [[ ! -d "$PROJECT_ROOT/.venv" ]]; then
  log "Creating Python virtualenv at $PROJECT_ROOT/.venv"
  "$PYTHON_CMD" -m venv "$PROJECT_ROOT/.venv"
  log "Installing backend requirements"
  "$PROJECT_ROOT/.venv/bin/pip" install -r "$PROJECT_ROOT/requirements.txt"
fi

cleanup() {
  local status="${EXIT_STATUS:-$?}"
  if [[ ${PIDS-} ]]; then
    for pid in "${PIDS[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
      fi
    done
  fi
  exit "$status"
}

# Activate Python virtualenv if present
if [[ -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1090
  source "$PROJECT_ROOT/.venv/bin/activate"
  log "Loaded Python virtualenv (.venv)"
else
  log "No local .venv detected, using current python interpreter"
fi

# Locate nvm
if [[ -z "${NVM_DIR:-}" ]]; then
  if [[ -d "$HOME/.nvm" ]]; then
    export NVM_DIR="$HOME/.nvm"
  elif [[ -d "/usr/local/opt/nvm" ]]; then
    export NVM_DIR="/usr/local/opt/nvm"
  fi
fi

if [[ -s "${NVM_DIR:-}/nvm.sh" ]]; then
  # shellcheck disable=SC1090
  source "$NVM_DIR/nvm.sh"
else
  echo "[dev] nvm is required but was not found. Install nvm and retry." >&2
  exit 1
fi

if [[ -f "$NVM_VERSION_FILE" ]]; then
  NODE_VERSION="$(tr -d ' \n' < "$NVM_VERSION_FILE")"
else
  NODE_VERSION="$FALLBACK_NODE_VERSION"
fi

if [[ -z "$NODE_VERSION" ]]; then
  NODE_VERSION="$FALLBACK_NODE_VERSION"
fi

log "Switching to Node ${NODE_VERSION} via nvm"
nvm install "$NODE_VERSION"
nvm use "$NODE_VERSION"

trap cleanup INT TERM

start_backend() {
  cd "$PROJECT_ROOT"
  log "Starting Django dev server at http://${DJANGO_ADDR}"
  python manage.py runserver "$DJANGO_ADDR"
}

start_frontend() {
  cd "$PROJECT_ROOT/frontend"
  log "Starting Vite dev server (npm run dev -- --host ${VITE_HOST})"
  npm run dev -- --host "$VITE_HOST"
}

parse_backend_address() {
  local addr="$DJANGO_ADDR"
  local host="${addr%:*}"
  local port="${addr##*:}"

  if [[ "$host" == "$addr" ]]; then
    # 未包含冒号，仅提供了端口或主机
    if [[ "$addr" =~ ^[0-9]+$ ]]; then
      host="127.0.0.1"
      port="$addr"
    else
      host="$addr"
      port="8000"
    fi
  fi

  if [[ -z "$host" || "$host" == "*" ]]; then
    host="127.0.0.1"
  fi

  if [[ -z "$port" || ! "$port" =~ ^[0-9]+$ ]]; then
    port="8000"
  fi

  BACKEND_LISTEN_HOST="$host"
  BACKEND_CONNECT_HOST="$host"
  if [[ "$host" == "0.0.0.0" ]]; then
    BACKEND_CONNECT_HOST="127.0.0.1"
  fi
  BACKEND_CONNECT_PORT="$port"
}

wait_for_backend() {
  local timeout="${BACKEND_READY_TIMEOUT:-60}"
  local start_ts
  start_ts=$(date +%s)
  log "Waiting for Django to accept connections on ${BACKEND_CONNECT_HOST}:${BACKEND_CONNECT_PORT} (timeout ${timeout}s)"
  while true; do
    if WAIT_HOST="$BACKEND_CONNECT_HOST" WAIT_PORT="$BACKEND_CONNECT_PORT" python - <<'PY' >/dev/null 2>&1; then
import os, socket
host = os.environ['WAIT_HOST']
port = int(os.environ['WAIT_PORT'])
s = socket.socket()
s.settimeout(1)
try:
    s.connect((host, port))
except OSError:
    raise SystemExit(1)
else:
    s.close()
    raise SystemExit(0)
PY
      log "Django server is ready."
      break
    fi

    if (( $(date +%s) - start_ts >= timeout )); then
      echo "[dev] Timed out waiting for Django to start on ${BACKEND_CONNECT_HOST}:${BACKEND_CONNECT_PORT}" >&2
      EXIT_STATUS=1
      cleanup
    fi
    sleep 1
  done
}

PIDS=()

parse_backend_address

start_backend &
PIDS+=("$!")

wait_for_backend

start_frontend &
PIDS+=("$!")

set +e
wait -n "${PIDS[@]}"
EXIT_STATUS=$?
set -e

log "One service exited (status ${EXIT_STATUS}), stopping the other..."
cleanup
