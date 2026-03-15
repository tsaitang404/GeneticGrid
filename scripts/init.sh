#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYENV_VERSION_FILE="$PROJECT_ROOT/.python-version"
NVM_VERSION_FILE="$PROJECT_ROOT/.nvmrc"
FALLBACK_NODE_VERSION="20.17.0"

log() {
  printf '[init] %s\n' "$*" >&2
}

error() {
  printf '[init] %s\n' "$*" >&2
}

resolve_python() {
  local python_bin=""

  if command -v pyenv >/dev/null 2>&1; then
    log "检测到 pyenv，正在初始化..."
    eval "$(pyenv init -)"

    if [[ -f "$PYENV_VERSION_FILE" ]]; then
      local version
      version="$(tr -d ' \n' < "$PYENV_VERSION_FILE")"
      if [[ -n "$version" ]]; then
        log "安装/启用 Python ${version}"
        pyenv install -s "$version"
        pyenv shell "$version"
      fi
    fi

    python_bin="$(pyenv which python)"
  elif command -v python3 >/dev/null 2>&1 && [[ -x "$(command -v python3)" ]]; then
    log "未检测到 pyenv，回退到系统 python3"
    python_bin="$(command -v python3)"
  elif command -v python >/dev/null 2>&1 && [[ -x "$(command -v python)" ]]; then
    log "未检测到 pyenv，回退到系统 python"
    python_bin="$(command -v python)"
  else
    error "未找到可用 Python，请先安装 Python 3.11+。"
    exit 1
  fi

  if [[ -z "$python_bin" || ! -x "$python_bin" ]]; then
    error "Python 解释器不可用。"
    exit 1
  fi

  printf '%s\n' "$python_bin"
}

setup_python() {
  local python_bin="$1"

  if [[ ! -d "$PROJECT_ROOT/.venv" ]]; then
    log "创建虚拟环境: .venv"
    "$python_bin" -m venv "$PROJECT_ROOT/.venv"
  fi

  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.venv/bin/activate"

  log "安装后端依赖"
  python -m pip install --upgrade pip
  pip install -r "$PROJECT_ROOT/requirements.txt"
}

setup_node() {
  if [[ -z "${NVM_DIR:-}" ]]; then
    export NVM_DIR="$HOME/.nvm"
  fi

  if [[ ! -s "$NVM_DIR/nvm.sh" ]]; then
    error "未找到 nvm，请先安装 nvm 后重试。"
    exit 1
  fi

  # shellcheck disable=SC1090
  source "$NVM_DIR/nvm.sh" --no-use

  local node_version="$FALLBACK_NODE_VERSION"
  if [[ -f "$NVM_VERSION_FILE" ]]; then
    node_version="$(tr -d ' \n' < "$NVM_VERSION_FILE")"
  fi

  log "安装/启用 Node ${node_version}"
  nvm install "$node_version"
  nvm use "$node_version"

  log "安装前端依赖 (npm ci)"
  (
    cd "$PROJECT_ROOT/frontend"
    npm ci
  )
}

setup_env_file() {
  if [[ -f "$PROJECT_ROOT/.env" ]]; then
    log "检测到 .env，跳过创建"
    return
  fi

  if [[ -f "$PROJECT_ROOT/.env.example" ]]; then
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    log "已从 .env.example 生成 .env"
  else
    : > "$PROJECT_ROOT/.env"
    log "未找到 .env.example，已创建空的 .env"
  fi
}

run_migrations() {
  if [[ -f "$PROJECT_ROOT/.env" ]]; then
    # 为本次 shell 加载变量，便于 migrate/check 使用
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
  fi

  log "执行数据库迁移"
  (
    cd "$PROJECT_ROOT"
    python manage.py migrate
    python manage.py check
  )
}

main() {
  cd "$PROJECT_ROOT"

  local python_bin
  python_bin="$(resolve_python)"

  setup_python "$python_bin"
  setup_node
  setup_env_file
  run_migrations

  log "本地环境初始化完成。"
  log "下一步可执行: ./scripts/dev.sh"
}

main "$@"
