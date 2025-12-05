#!/bin/bash

# GeneticGrid 后端代理配置快速启动脚本

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  GeneticGrid 代理功能 - 快速启动与测试                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="/data/code/GeneticGrid"
VENV_BIN="$PROJECT_ROOT/.venv/bin"

echo -e "${YELLOW}1. 检查 Python 虚拟环境${NC}"
if [ -f "$VENV_BIN/python" ]; then
    echo -e "${GREEN}✅ 虚拟环境已激活${NC}"
    PYTHON="$VENV_BIN/python"
else
    echo -e "${RED}❌ 虚拟环境未找到${NC}"
    exit 1
fi

echo
echo -e "${YELLOW}2. 检查代理配置${NC}"
cd "$PROJECT_ROOT"
$PYTHON manage.py proxy_status

echo
echo -e "${YELLOW}3. 测试代理功能${NC}"
echo "运行: python manage.py proxy_status --test"
echo
read -p "是否运行代理功能测试? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $PYTHON manage.py proxy_status --test
fi

echo
echo -e "${YELLOW}4. 启动 Django 服务器${NC}"
echo "运行: python manage.py runserver 0.0.0.0:8000"
echo
read -p "是否启动 Django 服务器? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $PYTHON manage.py runserver 0.0.0.0:8000
fi

echo
echo -e "${GREEN}✅ 快速启动脚本完成${NC}"
