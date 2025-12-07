# 数据源插件系统设计文档

**版本**: v2.0.0  
**日期**: 2025-01-05  
**状态**: 实现完成

---

## 目录

1. [概述](#概述)
2. [架构设计](#架构设计)
3. [核心组件](#核心组件)
4. [API 文档](#api-文档)
5. [快速开始](#快速开始)
6. [扩展指南](#扩展指南)
7. [最佳实践](#最佳实践)

---

## 概述

### 问题

之前的系统中，每个数据源（OKX、Binance、Coinbase 等）都是独立实现的服务类，存在以下问题：

- ❌ 缺乏统一的接口标准
- ❌ 每个数据源的能力和限制没有清晰的元数据描述
- ❌ 难以快速了解各数据源的支持情况
- ❌ 添加新数据源需要修改核心代码
- ❌ 没有自动化的能力文档生成机制

### 解决方案

实现一个标准化的数据源插件系统：

- ✅ 定义统一的 `MarketDataSourcePlugin` 基类
- ✅ 每个数据源必须声明其 `Capability` 和 `Metadata`
- ✅ 提供 `PluginManager` 进行统一管理
- ✅ 自动生成能力文档和 API 端点
- ✅ 支持动态加载和热更新

### 核心特点

1. **标准化接口**
   - 所有数据源都实现相同的方法：`get_candlesticks()`, `get_ticker()`
    - 使用统一的数据类：`CandleData`, `TickerData`, `FundingRateData`, `ContractBasisData`

2. **能力声明**
   - 每个数据源明确声明支持的粒度、交易对、限制等
   - 自动生成能力矩阵和对比表

3. **智能降级**
   - 请求不支持的粒度时，自动选择最接近的支持粒度
   - 用户无感知

4. **文档自动生成**
   - 根据插件的元数据自动生成 Markdown 文档
   - 生成 JSON 格式的能力描述
   - 提供 API 端点查询能力信息

---

## 架构设计

### 分层架构

```
┌─────────────────────────────────────┐
│      Frontend / API 客户端           │
└──────────────────┬──────────────────┘
                   │
         ┌─────────▼──────────┐
         │    Django Views    │
         │   (API 端点)        │
         └──────────┬─────────┘
                    │
         ┌──────────▼─────────┐
         │  PluginManager     │
         │  (插件管理)        │
         └─────┬────────┬─────┘
               │        │
       ┌───────▼─┐ ┌────▼───────┐
       │Metadata │ │Capability  │
       └─────────┘ └────────────┘
               │        │
    ┌──────────▼────────▼──────────┐
    │ MarketDataSourcePlugin(基类) │
    │ 定义标准接口                 │
    └──────────┬───────────────────┘
               │
    ┌──────────┴───────────────────┐
    │                              │
 ┌──▼───────┐ ┌──────────┐ ┌──────▼──┐
 │OKX Plugin│ │Binance   │ │Coinbase │
 │          │ │Plugin    │ │Plugin   │
 └──────────┘ └──────────┘ └─────────┘
```

### 组件关系图

```
┌─────────────────────────────────────────────────┐
│              PluginManager (单例)                │
│  • 注册插件                                      │
│  • 加载插件                                      │
│  • 获取插件                                      │
│  • 列出所有插件                                  │
└─────────────────────────────────────────────────┘
              ▲
              │ 管理
              │
    ┌─────────▼──────────┬──────────┐
    │                    │          │
 ┌──▼──┐            ┌────▼─┐   ┌──▼──┐
 │OKX  │            │Plugin│   │Docs │
 │Plugin            │Mgr   │   │Gen  │
 └─────┘            └──────┘   └─────┘
```

---

## 核心组件

### 1. MarketDataSourcePlugin (基类)

所有数据源必须继承此类。

```python
class MarketDataSourcePlugin(ABC):
    """数据源插件基类"""
    
    @abstractmethod
    def _get_metadata(self) -> DataSourceMetadata:
        """获取元数据"""
        pass
    
    @abstractmethod
    def _get_capability(self) -> Capability:
        """获取能力"""
        pass
    
    @abstractmethod
    def get_candlesticks(
        self,
        symbol: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
    ) -> List[CandleData]:
        """获取 K线数据"""
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> TickerData:
        """获取行情数据"""
        pass

    def get_funding_rate(self, symbol: str) -> FundingRateData:
        """可选：获取永续/期货合约的资金费率"""
        pass

    def get_contract_basis(
        self,
        symbol: str,
        contract_type: str = "perpetual",
        reference_symbol: Optional[str] = None,
        tenor: Optional[str] = None,
    ) -> ContractBasisData:
        """可选：获取指定合约的基差信息"""
        pass
```

### 2. DataSourceMetadata (元数据)

描述数据源的基本信息。

```python
@dataclass
class DataSourceMetadata:
    name: str                   # 唯一标识符
    display_name: str           # 显示名称
    description: str            # 描述
    source_type: SourceType     # 类型 (EXCHANGE/AGGREGATOR/CHARTING)
    website: Optional[str]      # 官网
    api_base_url: Optional[str] # API 基础 URL
    plugin_version: str         # 插件版本
    is_active: bool             # 是否激活
    is_experimental: bool       # 是否实验性
```

### 3. Capability (能力)

描述数据源支持的功能。

```python
@dataclass
class Capability:
    # K线相关
    supports_candlesticks: bool
    candlestick_granularities: List[str]  # ["1m", "5m", "1h", ...]
    candlestick_limit: int                # 单次最大条数
    candlestick_max_history_days: Optional[int]
    
    # 行情相关
    supports_ticker: bool
    ticker_update_frequency: Optional[int]
    
    # 交易对
    supported_symbols: List[str]
    symbol_format: str  # "BASE-QUOTE" 或 "BTCUSDT"
    
    # 限制和要求
    requires_api_key: bool
    requires_authentication: bool
    has_rate_limit: bool
    rate_limit_per_minute: Optional[int]
    
    # 高级特性
    supports_real_time: bool
    supports_websocket: bool
    
    # 衍生品指标
    supports_funding_rate: bool
    funding_rate_interval_hours: Optional[int]
    funding_rate_quote_currency: Optional[str]
    supports_contract_basis: bool
    contract_basis_types: List[str]
    contract_basis_tenors: List[str]
```

#### FundingRateData（资金费率）

```python
@dataclass
class FundingRateData:
    inst_id: str
    funding_rate: float
    timestamp: Optional[int]
    funding_interval_hours: Optional[int]
    next_funding_time: Optional[int]
    predicted_funding_rate: Optional[float]
    index_price: Optional[float]
    premium_index: Optional[float]
    quote_currency: Optional[str]
```

#### ContractBasisData（合约基差）

```python
@dataclass
class ContractBasisData:
    inst_id: str
    contract_type: str
    basis: float
    timestamp: Optional[int]
    basis_rate: Optional[float]
    contract_price: Optional[float]
    reference_symbol: Optional[str]
    reference_price: Optional[float]
    tenor: Optional[str]
    quote_currency: Optional[str]
```

### 4. PluginManager (管理器)

负责插件的注册、加载和管理。

```python
class PluginManager:
    """插件管理器（单例）"""
    
    def register_plugin(self, plugin: MarketDataSourcePlugin) -> None:
        """注册插件"""
        
    def get_plugin(self, name: str) -> Optional[MarketDataSourcePlugin]:
        """获取插件"""
        
    def get_all_plugins(self) -> Dict[str, MarketDataSourcePlugin]:
        """获取所有插件"""
        
    def list_plugin_names(self) -> List[str]:
        """列出插件名称"""
        
    def get_plugin_capability(self, name: str) -> Capability:
        """获取插件能力"""
```

### 5. DocumentationGenerator (文档生成器)

自动生成能力文档。

```python
class DocumentationGenerator:
    """文档生成器"""
    
    @staticmethod
    def generate_plugin_doc(plugin: MarketDataSourcePlugin) -> str:
        """生成单个插件的 Markdown 文档"""
        
    @staticmethod
    def generate_all_plugins_doc(manager: PluginManager) -> str:
        """生成所有插件的合并文档"""
        
    @staticmethod
    def generate_capabilities_json(manager: PluginManager) -> Dict:
        """生成 JSON 格式的能力描述"""
```

---

## API 文档

### 1. 获取所有数据源

**端点**: `GET /api/sources/`

**响应**:
```json
{
  "code": 0,
  "data": {
    "okx": {
      "metadata": {
        "name": "okx",
        "display_name": "OKX 交易所",
        "description": "...",
        "source_type": "exchange",
        ...
      },
      "capability": {
        "supports_candlesticks": true,
        "candlestick_granularities": ["1m", "5m", "15m", "1h", ...],
        ...
      }
    },
    "binance": { ... },
    "coinbase": { ... }
  },
  "total": 5
}
```

### 2. 获取特定数据源的能力

**端点**: `GET /api/sources/{source_name}/capabilities/`

**示例**: `/api/sources/coinbase/capabilities/`

**响应**:
```json
{
  "code": 0,
  "data": {
    "name": "coinbase",
    "metadata": { ... },
    "capability": { ... },
    "documentation": "# Coinbase 交易所\n..."
  }
}
```

### 3. 获取所有数据源文档

**端点**: `GET /api/documentation/sources/`

**响应**:
```json
{
  "code": 0,
  "data": {
    "markdown": "# 数据源插件文档\n...",
    "json": {
      "generated_at": "2025-01-05T...",
      "plugins": { ... }
    }
  }
}
```

### 4. K线数据（已优化）

**端点**: `GET /api/candlesticks/?source={source}&symbol=BTC-USDT&bar=1h&limit=10`

现在会进行数据源验证，返回更详细的错误信息。

### 5. 行情数据（已优化）

**端点**: `GET /api/ticker/?source={source}&symbol=BTC-USDT`

现在使用插件系统，支持所有注册的数据源。

---

## 快速开始

### 1. 列出所有插件

```bash
curl http://localhost:8000/api/sources/
```

### 2. 查询 OKX 的能力

```bash
curl http://localhost:8000/api/sources/okx/capabilities/
```

### 3. 获取数据

```bash
# 使用 OKX 获取 K线
curl 'http://localhost:8000/api/candlesticks/?source=okx&symbol=BTC-USDT&bar=1h&limit=10'

# 使用 Coinbase 获取行情
curl 'http://localhost:8000/api/ticker/?source=coinbase&symbol=BTC-USDT'
```

### 4. 生成文档

```bash
# 生成 Markdown 文档
python manage.py generate_plugin_docs --format markdown --output docs/sources.md

# 生成 JSON 格式
python manage.py generate_plugin_docs --format json --output docs/sources.json

# 两个都生成
python manage.py generate_plugin_docs --format both --output docs/sources

# 生成特定数据源文档
python manage.py generate_plugin_docs --source coinbase
```

### 5. 运行演示

```bash
python demo_plugins.py
```

---

## 扩展指南

### 添加新数据源

以下以添加 "Kraken" 数据源为例：

#### 步骤 1: 创建插件类

创建文件 `core/plugins/sources/kraken_plugin.py`:

```python
from ..base import (
    MarketDataSourcePlugin,
    DataSourceMetadata,
    Capability,
    CandleData,
    TickerData,
    SourceType,
    PluginError,
)

class KrakenMarketPlugin(MarketDataSourcePlugin):
    """Kraken 交易所数据源插件"""
    
    def _get_metadata(self) -> DataSourceMetadata:
        return DataSourceMetadata(
            name="kraken",
            display_name="Kraken 交易所",
            description="欧洲领先的加密资产交易平台",
            source_type=SourceType.EXCHANGE,
            website="https://www.kraken.com",
            api_base_url="https://api.kraken.com",
            plugin_version="1.0.0",
            is_active=True,
        )
    
    def _get_capability(self) -> Capability:
        return Capability(
            supports_candlesticks=True,
            candlestick_granularities=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
            candlestick_limit=720,
            supports_ticker=True,
            supported_symbols=[],  # 动态或无限制
            symbol_format="BASE-USD",
            has_rate_limit=True,
            rate_limit_per_minute=15,
        )
    
    def get_candlesticks(self, symbol: str, bar: str, limit: int = 100, before = None) -> List[CandleData]:
        # 实现 Kraken API 调用
        pass
    
    def get_ticker(self, symbol: str) -> TickerData:
        # 实现 Kraken API 调用
        pass
```

#### 步骤 2: 注册插件

在 `core/plugins/sources/__init__.py` 中添加:

```python
from .kraken_plugin import KrakenMarketPlugin

__all__ = [
    'OKXMarketPlugin',
    'BinanceMarketPlugin',
    'CoinbaseMarketPlugin',
    'CoinGeckoMarketPlugin',
    'TradingViewMarketPlugin',
    'KrakenMarketPlugin',  # 新增
]
```

#### 步骤 3: 自动注册

在 `core/plugin_init.py` 中的 `initialize_plugins()` 函数中添加:

```python
plugins_to_register = [
    OKXMarketPlugin,
    BinanceMarketPlugin,
    CoinbaseMarketPlugin,
    CoinGeckoMarketPlugin,
    TradingViewMarketPlugin,
    KrakenMarketPlugin,  # 新增
]
```

完成！新数据源会自动被加载和注册。

---

## 最佳实践

### 1. 错误处理

```python
def get_candlesticks(self, symbol: str, bar: str, limit: int = 100, before = None):
    try:
        # 调用 API
        response = self._api_client.get_candles(...)
        
        # 转换为标准格式
        candles = [CandleData(...) for item in response]
        return candles
    except Exception as e:
        logger.error(f"API 调用失败: {e}")
        raise PluginError(f"获取 K线数据失败: {e}")
```

### 2. 能力声明

准确声明支持的功能和限制，避免误导用户：

```python
def _get_capability(self) -> Capability:
    return Capability(
        supports_candlesticks=True,
        candlestick_granularities=self._get_supported_granularities(),
        candlestick_limit=self._get_max_limit(),
        candlestick_max_history_days=365,
        supports_ticker=True,
        requires_api_key=True,  # 准确声明
        has_rate_limit=True,
        rate_limit_per_minute=10,
    )
```

### 3. 数据转换

确保返回的数据格式正确：

```python
def get_ticker(self, symbol: str) -> TickerData:
    response = self._api.get_ticker(symbol)
    
    # 确保类型转换正确
    return TickerData(
        inst_id=symbol,
        last=float(response['price']),
        bid=float(response.get('bid', 0)) or None,
        ask=float(response.get('ask', 0)) or None,
    )
```

### 4. 粒度支持

如果不支持某个粒度，在 `_get_capability()` 中明确声明，不要在运行时才报错。

### 5. 缓存和性能

考虑实现缓存以减少 API 调用：

```python
class MyPlugin(MarketDataSourcePlugin):
    def __init__(self):
        super().__init__()
        self._ticker_cache = {}
        self._cache_time = 0
    
    def get_ticker(self, symbol: str) -> TickerData:
        # 缓存逻辑
        if time.time() - self._cache_time < 60:
            if symbol in self._ticker_cache:
                return self._ticker_cache[symbol]
        
        # 获取新数据
        ticker = self._fetch_from_api(symbol)
        self._ticker_cache[symbol] = ticker
        self._cache_time = time.time()
        return ticker
```

---

## 文件结构

```
core/plugins/
├── __init__.py              # 包导出
├── base.py                  # 基类和数据结构
├── manager.py               # 插件管理器
├── documentation.py         # 文档生成器
└── sources/
    ├── __init__.py          # 源导出
    ├── okx_plugin.py        # OKX 插件
    ├── binance_plugin.py    # Binance 插件
    ├── coinbase_plugin.py   # Coinbase 插件
    ├── coingecko_plugin.py  # CoinGecko 插件
    └── tradingview_plugin.py # TradingView 插件

core/
├── plugin_init.py           # 插件初始化
├── apps.py                  # Django App 配置（集成初始化）
├── views.py                 # 更新了 API 端点
├── urls.py                  # 新增路由

core/management/commands/
└── generate_plugin_docs.py  # 文档生成命令
```

---

## 总结

这个标准化的数据源插件系统提供了：

✅ **统一接口**: 所有数据源遵循相同的 API 合约  
✅ **清晰的能力描述**: 每个插件明确声明其支持的功能  
✅ **易于扩展**: 添加新数据源只需创建新插件类  
✅ **自动文档生成**: 根据能力自动生成 Markdown 和 JSON 文档  
✅ **智能降级**: 不支持的粒度自动选择最接近的替代  
✅ **完整的 API**: 提供端点查询所有数据源的信息  
✅ **向后兼容**: 保留旧的 API 端点，过渡期内两个系统并行运行  

---

**下一步**: 逐步迁移前端和其他系统使用新的插件系统，最终完全替代旧的服务类架构。
