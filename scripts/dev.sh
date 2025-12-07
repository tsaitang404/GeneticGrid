#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_NODE_VERSION="20.17.0"
DJANGO_ADDR="${DJANGO_ADDR:-127.0.0.1:8000}"
VITE_HOST="${VITE_HOST:-0.0.0.0}"

log() {
  printf '[dev] %s\n' "$*"
}

if command -v pyenv >/dev/null 2>&1; then
  log "Initializing pyenv"
  eval "$(pyenv init -)"
else
  log "pyenv not detected, falling back to system Python"
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

log "Switching to Node ${DEFAULT_NODE_VERSION} via nvm"
nvm use "$DEFAULT_NODE_VERSION"

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

PIDS=()

start_backend &
PIDS+=("$!")
start_frontend &
PIDS+=("$!")

set +e
wait -n "${PIDS[@]}"
EXIT_STATUS=$?
set -e

log "One service exited (status ${EXIT_STATUS}), stopping the other..."
cleanup
