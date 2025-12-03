# GeneticGrid - 加密货币交易平台

基于 **Vue 3 + TypeScript + Django** 的现代化加密货币K线图分析平台。

## ✨ 特性

- 🚀 **Vue 3 + TypeScript**: 完整的类型安全前端应用
- 📊 **22 种技术指标**: MA, EMA, BOLL, MACD, RSI, KDJ 等
- 🎨 **画线工具**: 直线、射线、斐波那契回调、等距通道
- 🔄 **多数据源**: TradingView, Binance, CoinGecko, OKX
- 💱 **15 种货币**: 支持多货币单位和实时汇率转换
- ⚡ **Web Worker**: 异步计算指标，不阻塞UI
- 🎯 **无限滚动**: 自动加载历史和实时数据

## 📦 技术栈

**前端**: Vue 3 + TypeScript + Vite + Lightweight Charts  
**后端**: Django 4.2 + Python 3.11+

## 🚀 快速开始

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

## 📁 项目结构

```
frontend/src/
  ├── components/  # Vue 组件
  ├── composables/ # 可复用逻辑
  └── types/       # TypeScript 类型
core/              # Django 应用
static/dist/       # Vue 构建输出
```

## 🎯 功能

- **22个技术指标**: MA, EMA, BOLL, SAR, MACD, RSI, KDJ, CCI, WR, OBV 等
- **画线工具**: 直线, 射线, 横线, 斐波那契, 等距通道
- **30+时间周期**: 支持自定义周期（如 2h, 7d）
- **15种货币**: USDT, USD, CNY, EUR, JPY 等

## 📄 许可证

MIT
