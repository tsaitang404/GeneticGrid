# 数据源插件系统 - 快速参考

## 📦 系统概览

一个标准化、可扩展的数据源插件架构，支持多交易所和数据聚合器的统一接口。

```
所有数据源 (OKX, Binance, Coinbase, etc.)
         ↓
  MarketDataSourcePlugin 基类
         ↓
    PluginManager (单例)
         ↓
   Django Views (API)
         ↓
    前端应用
```

---

## 🚀 快速开始

### 查询可用数据源

```bash
curl http://localhost:8000/api/sources/
```

### 查询数据源能力

```bash
curl http://localhost:8000/api/sources/okx/capabilities/
```

### 获取 K线数据

```bash
curl 'http://localhost:8000/api/candlesticks/?source=coinbase&symbol=BTC-USDT&bar=1h&limit=10'
```

### 获取行情数据

```bash
curl 'http://localhost:8000/api/ticker/?source=binance&symbol=ETH-USDT'
```

### 生成文档

```bash
python manage.py generate_plugin_docs --format markdown --output docs/sources.md
```

### 运行演示

```bash
python demo_plugins.py
```

---

## 📚 API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/sources/` | GET | 列出所有数据源 |
| `/api/sources/{name}/capabilities/` | GET | 查询数据源能力 |
| `/api/documentation/sources/` | GET | 获取完整文档 |
| `/api/candlesticks/` | GET | 获取 K线数据 |
| `/api/ticker/` | GET | 获取行情数据 |

---

## 🔧 核心类

### MarketDataSourcePlugin (基类)

所有数据源必须继承此类。

**必须实现的方法:**
- `_get_metadata()` → DataSourceMetadata
- `_get_capability()` → Capability
- `get_candlesticks(symbol, bar, limit, before, mode='spot')` → List[CandleData]
- `get_ticker(symbol, mode='spot')` → TickerData

**可选的方法:**
- `get_funding_rate(symbol)` → FundingRateData
- `get_contract_basis(symbol, contract_type='perpetual', reference_symbol=None, tenor=None)` → ContractBasisData

**可用的方法:**
- `get_metadata()` → DataSourceMetadata
- `get_capability()` → Capability
- `get_supported_symbols()` → List[str]
- `validate_symbol(symbol)` → bool
- `validate_granularity(bar)` → bool
- `get_closest_granularity(bar)` → Optional[str]

> `mode` 参数遵循 `SymbolMode`（`spot` 或 `contract`）。插件需在 `Capability.symbol_modes` 中声明支持的模式，接口会自动校验。

### DataSourceMetadata

```python
@dataclass
class DataSourceMetadata:
    name: str                   # 唯一标识符
    display_name: str           # 显示名称
    description: str            # 描述
    source_type: SourceType     # EXCHANGE / AGGREGATOR / CHARTING
    website: Optional[str]
    api_base_url: Optional[str]
    plugin_version: str
    is_active: bool
    is_experimental: bool
```

### Capability

```python
@dataclass
class Capability:
    supports_candlesticks: bool
    candlestick_granularities: List[str]
    candlestick_limit: int
    supports_ticker: bool
    ticker_update_frequency: Optional[int]
    supported_symbols: List[str]
    symbol_format: str
    symbol_modes: List[str]          # ['spot', 'contract'] 支持的交易模式
    requires_api_key: bool
    has_rate_limit: bool
    rate_limit_per_minute: Optional[int]
    supports_real_time: bool
    supports_websocket: bool
    supports_funding_rate: bool
    funding_rate_interval_hours: Optional[int]
    funding_rate_quote_currency: Optional[str]
    supports_contract_basis: bool
    contract_basis_types: List[str]
    contract_basis_tenors: List[str]
```

### CandleData

```python
@dataclass
class CandleData:
    time: int       # Unix 时间戳（秒）
    open: float
    high: float
    low: float
    close: float
    volume: float
```

### TickerData

```python
@dataclass
class TickerData:
    inst_id: str
    last: float
    bid: Optional[float]
    ask: Optional[float]
    high_24h: Optional[float]
    low_24h: Optional[float]
    change_24h: Optional[float]
    change_24h_pct: Optional[float]
```

### FundingRateData

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

### ContractBasisData

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

### PluginManager

```python
manager = get_plugin_manager()  # 获取单例

# 常用方法
plugin = manager.get_plugin('okx')
all_plugins = manager.get_all_plugins()
names = manager.list_plugin_names()
capability = manager.get_plugin_capability('binance')
```

---

## 📝 使用示例

### Python 代码

```python
from core.plugins.manager import get_plugin_manager

manager = get_plugin_manager()

# 获取 OKX 插件
plugin = manager.get_plugin('okx')

# 获取 K线数据
candles = plugin.get_candlesticks('BTC-USDT', '1h', limit=10)
for candle in candles:
    print(f"时间: {candle.time}, 收盘: {candle.close}")

# 获取行情数据
ticker = plugin.get_ticker('BTC-USDT')
print(f"BTC 最新价格: ${ticker.last}")

# 查询能力
capability = plugin.get_capability()
print(f"支持粒度: {capability.candlestick_granularities}")
print(f"速率限制: {capability.rate_limit_per_minute}/分钟")

if capability.supports_funding_rate:
    funding = plugin.get_funding_rate('BTC-USDT')
    print(f"资金费率: {funding.funding_rate:.4%}, 下次结算: {funding.next_funding_time}")

if capability.supports_contract_basis:
    basis = plugin.get_contract_basis('BTC-USDT', contract_type='perpetual', reference_symbol='BTCUSDT-SPOT')
    basis_rate_display = f"{basis.basis_rate:.4%}" if basis.basis_rate is not None else "N/A"
    print(f"当前基差: {basis.basis} ({basis_rate_display})")
```

### API 调用

```python
import requests

# 获取所有数据源
resp = requests.get('http://localhost:8000/api/sources/')
sources = resp.json()['data']

# 查询 OKX 能力
resp = requests.get('http://localhost:8000/api/sources/okx/capabilities/')
okx_info = resp.json()['data']

# 获取 K线
params = {
    'source': 'coinbase',
    'symbol': 'BTC-USDT',
    'bar': '4h',
    'limit': 10
}
resp = requests.get('http://localhost:8000/api/candlesticks/', params=params)
candles = resp.json()['data']
```

---

## ➕ 添加新数据源

### 步骤 1: 创建插件类

```python
# core/plugins/sources/kraken_plugin.py

from ..base import MarketDataSourcePlugin, DataSourceMetadata, Capability, SourceType

class KrakenMarketPlugin(MarketDataSourcePlugin):
    def _get_metadata(self) -> DataSourceMetadata:
        return DataSourceMetadata(
            name="kraken",
            display_name="Kraken 交易所",
            description="欧洲领先的加密资产交易平台",
            source_type=SourceType.EXCHANGE,
            website="https://www.kraken.com",
            api_base_url="https://api.kraken.com",
        )
    
    def _get_capability(self) -> Capability:
        return Capability(
            supports_candlesticks=True,
            candlestick_granularities=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
            candlestick_limit=720,
            supports_ticker=True,
            has_rate_limit=True,
            rate_limit_per_minute=15,
        )
    
    def get_candlesticks(self, symbol, bar, limit=100, before=None):
        # 调用 Kraken API 并返回 List[CandleData]
        pass
    
    def get_ticker(self, symbol):
        # 调用 Kraken API 并返回 TickerData
        pass
```

### 步骤 2: 注册插件

在 `core/plugins/sources/__init__.py` 中:
```python
from .kraken_plugin import KrakenMarketPlugin

__all__ = [
    ...,
    'KrakenMarketPlugin',  # 新增
]
```

在 `core/plugin_init.py` 中:
```python
from .plugins.sources import KrakenMarketPlugin

plugins_to_register = [
    ...,
    KrakenMarketPlugin,  # 新增
]
```

完成！插件会自动加载。

---

## 📋 已注册的数据源

| 名称 | 类型 | K线 | 行情 | 粒度数 | 状态 |
|------|------|-----|------|--------|------|
| okx | EXCHANGE | ✅ | ✅ | 12 | ✅ |
| binance | EXCHANGE | ✅ | ✅ | 14 | ✅ |
| coinbase | EXCHANGE | ✅ | ✅ | 7 | ✅ |
| coingecko | AGGREGATOR | ❌ | ✅ | - | ✅ |
| tradingview | CHARTING | ✅ | ✅ | 14 | ✅ |

---

## 🎯 粒度支持

### OKX
`1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M`

### Binance
`1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M`

### Coinbase
`1m, 5m, 15m, 1h, 4h, 1d, 1w`
(4h → 6h, 1w → 1d)

---

## 🔍 调试

### 列出所有插件

```python
from core.plugins.manager import get_plugin_manager

manager = get_plugin_manager()
print(manager.list_plugin_names())
# 输出: ['okx', 'binance', 'coinbase', 'coingecko', 'tradingview']
```

### 检查插件状态

```python
plugin = manager.get_plugin('okx')
print(f"名称: {plugin.display_name}")
print(f"活跃: {plugin.get_metadata().is_active}")
print(f"支持 K线: {plugin.get_capability().supports_candlesticks}")
```

### 验证数据源

```python
plugin = manager.get_plugin('coinbase')

# 验证交易对
is_valid = plugin.validate_symbol('BTC-USDT')

# 验证粒度
is_supported = plugin.validate_granularity('1h')

# 获取最接近的粒度
closest = plugin.get_closest_granularity('4h')  # 返回 '1h'
```

---

## 📁 文件位置

```
core/plugins/
├── base.py                  # 基类和数据结构
├── manager.py               # 插件管理器
├── documentation.py         # 文档生成
└── sources/
    ├── okx_plugin.py
    ├── binance_plugin.py
    ├── coinbase_plugin.py
    ├── coingecko_plugin.py
    └── tradingview_plugin.py

core/plugin_init.py          # 初始化脚本
core/apps.py                 # Django 配置
core/views.py                # API 视图
core/urls.py                 # 路由

demo_plugins.py              # 演示脚本
PLUGIN_SYSTEM_DESIGN.md      # 完整设计文档
```

---

## 🔗 相关资源

- **设计文档**: `PLUGIN_SYSTEM_DESIGN.md`
- **实现详情**: `PLUGIN_SYSTEM_IMPLEMENTATION.md`
- **演示脚本**: `demo_plugins.py`
- **API 端点**: 见上文

---

## 💡 常见问题

### Q: 如何添加新的粒度支持？

在 `core/plugins/base.py` 的 `Granularity` 类中更新 `GRANULARITIES` 字典：

```python
class Granularity:
    GRANULARITIES = {
        ...
        "2h": 7200,  # 新增
        "3d": 259200,  # 新增
    }
```

### Q: 如何禁用某个数据源？

在插件的 `_get_metadata()` 方法中设置 `is_active=False`：

```python
def _get_metadata(self) -> DataSourceMetadata:
    return DataSourceMetadata(
        ...
        is_active=False,  # 禁用
    )
```

### Q: 如何自定义文档？

使用 `DocumentationGenerator` 类：

```python
from core.plugins.documentation import DocumentationGenerator

doc = DocumentationGenerator.generate_plugin_doc(plugin)
json_data = DocumentationGenerator.generate_capabilities_json(manager)
```

---

## ✅ 检查清单

启动应用时的初始化检查：

- [ ] Django 应用启动
- [ ] 插件管理器初始化
- [ ] 5 个默认插件加载
- [ ] API 端点就绪
- [ ] 前端能访问 `/api/sources/`

---

## 📞 支持

- 查看设计文档: `PLUGIN_SYSTEM_DESIGN.md`
- 查看实现详情: `PLUGIN_SYSTEM_IMPLEMENTATION.md`
- 运行演示: `python demo_plugins.py`
- 检查日志: 应用启动时会输出插件加载信息

---

**版本**: v2.0.0  
**最后更新**: 2025-01-05  
**状态**: ✅ 生产就绪
