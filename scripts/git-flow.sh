#!/usr/bin/env bash
# Git 工作流：自动拉取 → 检查 → 提交 → 推送
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

log() { printf '[git-flow] %s\n' "$*"; }

# 1. 拉取最新代码
log "拉取最新代码..."
git pull --rebase
log "拉取完成"

# 2. 显示当前状态
echo ""
git status --short
echo ""

# 3. 如果有变更，引导用户提交
if [[ -z "$(git status --porcelain)" ]]; then
    log "工作区干净，无需提交"
    exit 0
fi

log "检测到变更，正在执行 pre-commit 校验..."
# pre-commit 会自动运行（已安装到 git hooks）
# 但这里也显式执行一次确保开发环境有 pre-commit
if command -v pre-commit &>/dev/null; then
    pre-commit run --all-files || {
        echo ""
        log "❌ 校验未通过，请修复后重试"
        exit 1
    }
fi

log "✅ 校验通过"

# 4. 提交（允许用户指定提交信息）
if [[ $# -ge 1 ]]; then
    git add -A
    git commit -m "$*"
    log "已提交: $*"
else
    echo ""
    log "请输入提交信息，或按 Ctrl+C 取消："
    read -r msg
    if [[ -z "$msg" ]]; then
        log "提交已取消"
        exit 0
    fi
    git add -A
    git commit -m "$msg"
    log "已提交: $msg"
fi

# 5. 推送
log "推送到远程..."
git push
log "✅ 推送完成"
