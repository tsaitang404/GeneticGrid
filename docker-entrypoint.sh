#!/bin/sh
# GeneticGrid Docker 启动入口
#
# 环境变量控制：
#   USE_GUNICORN=true        → 使用 gunicorn + uvicorn worker（生产模式）
#   不设置或 false           → 使用 Django runserver（开发模式，默认）
#
#   GUNICORN_WORKERS=4        gunicorn worker 进程数（默认 4）
#   GUNICORN_PORT=8000        监听端口（默认 8000）

set -e

WORKERS="${GUNICORN_WORKERS:-4}"
PORT="${GUNICORN_PORT:-8000}"

# 始终执行数据库迁移
echo "→ Running database migrations..."
python manage.py migrate --noinput

# 预热交易对列表缓存（避免首次页面加载时等待 OKX API）
echo "→ Warming symbol cache..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
import django; django.setup()
from django.test import Client
c = Client()
c.get('/api/account/symbols/?type=SPOT')
c.get('/api/account/symbols/?type=SWAP')
print('  ✓ SPOT + SWAP cached')
" 2>&1

if [ "${USE_GUNICORN}" = "true" ] || [ "${USE_GUNICORN}" = "1" ]; then
    echo "→ Starting gunicorn (production mode) on 0.0.0.0:${PORT} with ${WORKERS} workers..."
    exec gunicorn \
        -w "${WORKERS}" \
        -k uvicorn.workers.UvicornWorker \
        -b "0.0.0.0:${PORT}" \
        --max-requests 10000 \
        --max-requests-jitter 1000 \
        --timeout 60 \
        --graceful-timeout 30 \
        --access-logfile - \
        --error-logfile - \
        geneticgrid.asgi:application
else
    echo "→ Starting Django runserver (development mode) on 0.0.0.0:${PORT}..."
    exec python manage.py runserver "0.0.0.0:${PORT}"
fi
