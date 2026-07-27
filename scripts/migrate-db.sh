#!/usr/bin/env bash
# GeneticGrid 数据库迁移辅助脚本
#
# 用法:
#   ./scripts/migrate-db.sh check          # 检查数据库状态
#   ./scripts/migrate-db.sh import         # 从 SQLite 导入历史数据到 PostgreSQL
#   ./scripts/migrate-db.sh prune          # 清理过期数据
#   ./scripts/migrate-db.sh vacuum         # 数据库维护（VACUUM ANALYZE）

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
MANAGE="python manage.py"

if [[ -f "$VENV_PYTHON" ]]; then
    MANAGE="$VENV_PYTHON manage.py"
fi

info()  { echo -e "\033[0;34m[INFO]\033[0m $*"; }
ok()    { echo -e "\033[0;32m[OK]\033[0m $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m $*"; }
error() { echo -e "\033[0;31m[ERROR]\033[0m $*"; }

check() {
    info "检查 PostgreSQL 状态..."
    $MANAGE dbshell -c "SELECT current_database(), version();" 2>/dev/null || \
        error "无法连接数据库，请检查 DATABASE_URL 配置"

    info "K 线数据统计..."
    $MANAGE shell -c "
from core.models import CandlestickCache
from django.db import connection
print(f'  数据库引擎: {connection.vendor}')
print(f'  总行数: {CandlestickCache.objects.count():,}')
print(f'  数据源: {list(CandlestickCache.objects.values_list(\"source\", flat=True).distinct())}')
" 2>/dev/null || error "查询失败"
}

import_data() {
    info "从 SQLite 导入历史数据到 PostgreSQL..."
    $MANAGE migrate_to_pg "$@"
}

prune() {
    info "清理过期 K 线数据..."
    $MANAGE prune_candles "$@"
}

vacuum() {
    info "执行数据库维护（VACUUM ANALYZE）..."
    $MANAGE dbshell -c "VACUUM ANALYZE;" 2>/dev/null || \
        error "VACUUM 失败"
    ok "数据库维护完成"
}

case "${1:-}" in
    check)   check ;;
    import)  shift; import_data "$@" ;;
    prune)   shift; prune "$@" ;;
    vacuum)  vacuum ;;
    *)
        echo "GeneticGrid 数据库迁移工具"
        echo ""
        echo "用法: $0 <command> [options]"
        echo ""
        echo "命令:"
        echo "  check      检查当前 PostgreSQL 状态"
        echo "  import     从 SQLite 导入历史数据到 PostgreSQL"
        echo "  prune      清理过期数据 (--days N --dry-run)"
        echo "  vacuum     数据库维护（VACUUM ANALYZE）"
        ;;
esac
