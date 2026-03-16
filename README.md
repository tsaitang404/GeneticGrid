# GeneticGrid - 加密货币交易平台

基于 **Vue 3 + TypeScript + Django** 的现代化加密货币K线图分析平台。

## ✨ 特性

- 🚀 **Vue 3 + TypeScript**: 完整的类型安全前端应用
- 📊 **22 种技术指标**: MA, EMA, BOLL, MACD, RSI, KDJ 等
- 🎨 **画线工具**: 直线、射线、斐波那契回调、等距通道
- 🔄 **多数据源**: OKX, Binance, Coinbase, CoinGecko, TradingView
- 💱 **15 种货币**: 支持多货币单位和实时汇率转换
- ⚡ **Web Worker**: 异步计算指标，不阻塞UI
- 🎯 **无限滚动**: 自动加载历史和实时数据
- 🌍 **全球交易所覆盖**: 支持北美(Coinbase)、亚洲(OKX/币安)等主要市场

## 📦 技术栈

**前端**: Vue 3 + TypeScript + Vite + Lightweight Charts  
**后端**: Django 4.2 + Python 3.11+

## �️ 环境准备（pyenv + nvm）

使用 [pyenv](https://github.com/pyenv/pyenv) 与 [nvm](https://github.com/nvm-sh/nvm) 可以为 Python 和 Node.js 创建可重复的开发环境。


### 🧰 一键初始化本地环境

项目提供初始化脚本，可自动完成以下操作：
- 根据 `.python-version` 安装并启用 Python（优先 pyenv）
- 创建 `.venv` 并安装后端依赖
- 根据 `.nvmrc` 安装并启用 Node（通过 nvm）
- 在 `frontend/` 执行 `npm ci`
- 从 `.env.example` 生成 `.env`（若不存在）
- 执行 `python manage.py migrate` 与 `python manage.py check`

```bash
./scripts/init.sh
```

初始化完成后可直接启动开发环境：

```bash
./scripts/dev.sh
```

### ⚙️ 一键启动前后端

如果想在同一个终端里同时启动 Django 与 Vite，可使用项目自带脚本：

```bash
./scripts/dev.sh
```

脚本会自动创建缺失的 `.venv`、安装 `requirements.txt`，然后依据 `.python-version` 使用 `pyenv` 激活对应解释器；接着读取 `.nvmrc`（若缺失则回退到 20.17.0）并通过 `nvm use` 启动对应的 Node 版本，最后分别运行 `python manage.py runserver` 与 `npm run dev -- --host 0.0.0.0`。可通过环境变量来自定义监听地址：

```bash
DJANGO_ADDR=0.0.0.0:8000 VITE_HOST=127.0.0.1 ./scripts/dev.sh
```

> 提示：脚本会在启动前执行 `pyenv init -` 并读取 `.python-version` / `.nvmrc`，确保 Python 与 Node 均使用项目锁定的版本，并会等待 Django 端口就绪后再启动前端，避免初次请求命中未就绪的 API。

按 `Ctrl+C` 将同时停止前后端进程。
### Python（pyenv）

```bash
# 安装项目所需的 Python 版本
pyenv install 3.11.9

# 将当前目录固定为该版本
pyenv local 3.11.9

# 可选：使用 pyenv-virtualenv 管理独立的虚拟环境
pyenv virtualenv 3.11.9 geneticgrid
pyenv activate geneticgrid

# 安装后端依赖
pip install -r requirements.txt
```

> 如果你更倾向于使用系统 Python，也可以通过 `python -m venv .venv && source .venv/bin/activate` 来创建虚拟环境，确保最终使用的是 3.11.x 版本。

### Node.js（nvm）

```bash
# 安装并启用项目指定的 Node.js 版本
nvm install 20.17.0
nvm use

# 安装前端依赖
cd frontend
npm install
```

## �🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt
cd frontend && npm install

# 2. 开发模式
# 终端1: Django API
python manage.py runserver

# 终端2: Vite 开发服务器  
cd frontend && npm run dev
# 访问: http://localhost:3000

# 3. 生产部署
cd frontend && npm run build
python manage.py runserver
# 访问: http://127.0.0.1:8000
```

## ✅ 单元测试

安装依赖后可直接运行：

```bash
pytest
```

如果使用项目虚拟环境，推荐：

```bash
./.venv/bin/python -m pytest
```

覆盖率报告示例：

```bash
./.venv/bin/python -m pytest --cov=core --cov=geneticgrid --cov-report=term-missing
```

## 📁 项目结构

```
frontend/src/
  ├── components/  # Vue 组件
  ├── composables/ # 可复用逻辑
  └── types/       # TypeScript 类型
core/              # Django 应用
static/dist/       # Vue 构建输出
```

## 🐳 Docker 打包与运行

项目已提供 GitHub Container Registry 镜像，推荐直接从 GitHub 镜像仓库拉取并运行；如需本地定制，再自行构建镜像。

```bash
# 1) 拉取 GitHub 镜像
docker pull ghcr.io/tsaitang404/geneticgrid:v0.2.1

# 2) 直接按默认值启动（无需 .env、无需额外环境变量）
./scripts/docker-run.sh
```

如果你需要自定义配置，再额外提供 `.env` 或 shell 环境变量。

使用 `.env` 文件时：

```bash
cp .env.example .env
# 按需编辑 .env
./scripts/docker-run.sh
```

使用当前 shell 或 CI 注入的环境变量时：

```bash
PROXY_ENABLED=true \
HTTP_PROXY_HOST=127.0.0.1 \
HTTP_PROXY_PORT=8080 \
./scripts/docker-run.sh
```

如需本地自行构建镜像：

```bash
docker build -t geneticgrid:local .
IMAGE=geneticgrid:local ./scripts/docker-run.sh
```

访问地址：`http://127.0.0.1:8000`

如需手动运行并持久化配置/数据库，可按需挂载 `.env`，也可只传 Docker 环境变量：

```bash
docker run --name geneticgrid -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/.env:/app/.env:ro \
  -v $(pwd)/db.sqlite3:/app/db.sqlite3 \
  ghcr.io/tsaitang404/geneticgrid:v0.2.1
```

不使用 `.env` 文件时：

```bash
docker run --name geneticgrid -p 8000:8000 \
  -e PROXY_ENABLED=true \
  -e HTTP_PROXY_HOST=127.0.0.1 \
  -e HTTP_PROXY_PORT=8080 \
  -v $(pwd)/db.sqlite3:/app/db.sqlite3 \
  ghcr.io/tsaitang404/geneticgrid:v0.2.1
```

完全使用默认配置时：

```bash
docker run --name geneticgrid -p 8000:8000 \
  -v $(pwd)/db.sqlite3:/app/db.sqlite3 \
  ghcr.io/tsaitang404/geneticgrid:v0.2.1
```

如需在容器中使用宿主机代理（默认 SOCKS5 端口 `1080`、HTTP 端口 `8080`），推荐写入 `.env` 后直接使用 `./scripts/docker-run.sh`。

`.env` 示例：

```bash
PROXY_ENABLED=true
PROXY_CONTAINER_AUTO_HOST=true
PROXY_CONTAINER_HOST=host.docker.internal
PROXY_CONTAINER_NETWORK_MODE=auto
HTTP_PROXY_HOST=127.0.0.1
HTTP_PROXY_PORT=8080
SOCKS5_PROXY_HOST=127.0.0.1
SOCKS5_PROXY_PORT=1080
```

等价的手动命令：

```bash
docker run --name geneticgrid -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/.env:/app/.env:ro \
  -v $(pwd)/db.sqlite3:/app/db.sqlite3 \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/tsaitang404/geneticgrid:v0.2.1
```

说明：
- 当 `PROXY_CONTAINER_NETWORK_MODE=auto` 时，若在 Linux 上检测到代理主机配置为 `127.0.0.1` 或 `localhost`，启动脚本会自动切换为 `--network host`，避免 bridge 网络下无法访问宿主机回环代理。
- 如果你明确知道代理可通过 `host.docker.internal` 访问，可将 `PROXY_CONTAINER_NETWORK_MODE=bridge` 固定为 bridge 模式。
- 如果你明确要共享宿主机网络，也可将 `PROXY_CONTAINER_NETWORK_MODE=host` 固定为 host 模式。
- 当 `PROXY_CONTAINER_AUTO_HOST=true` 且应用运行在容器内时，若代理主机配置为 `127.0.0.1` 或 `localhost`，后端会自动改用 `PROXY_CONTAINER_HOST`（默认 `host.docker.internal`）。
- 这样可以避免容器把 `127.0.0.1` 解析为容器自身，导致代理不可达。
- `host-gateway` 会自动解析宿主机网关地址，宿主机 IP 变化时无需改容器参数。

### 自动打包镜像

仓库已配置 GitHub Actions，在推送符合 `vX.Y.Z` 格式的 tag 时自动构建并发布镜像到 GitHub Container Registry：

```bash
git tag v1.0.0
git push origin v1.0.0
```

发布后的镜像地址为：

```text
ghcr.io/<github-owner>/geneticgrid:v1.0.0
```

实际镜像名会自动使用 GitHub 仓库名的小写形式，即 `ghcr.io/<owner>/<repo>:<tag>`。

首次使用前请确认仓库启用了 Packages 权限；该 workflow 使用 GitHub 自带的 `GITHUB_TOKEN` 推送镜像，无需额外的仓库 Secrets。

## 🎯 功能

- **22个技术指标**: MA, EMA, BOLL, SAR, MACD, RSI, KDJ, CCI, WR, OBV 等
- **画线工具**: 直线, 射线, 横线, 斐波那契, 等距通道
- **30+时间周期**: 支持自定义周期（如 2h, 7d）
- **15种货币**: USDT, USD, CNY, EUR, JPY 等

## 📄 许可证

MIT
