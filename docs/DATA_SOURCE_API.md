# 数据源能力 API 文档

## 概述

每个数据源插件独立注册自己支持的交易对、K线周期等能力信息。前端可以通过 API 动态获取这些信息，实现智能化的数据源选择和降级策略。

## 统一协议

### 交易对格式
- **标准格式**: `BTCUSDT`（无分隔符，大写）
- 前端统一使用此格式
- 插件内部自动转换为各自格式：
  - OKX: `BTC-USDT`
  - Binance: `BTCUSDT`
  - Coinbase: `BTC-USD`
  - CoinGecko: `bitcoin`

### 时间粒度格式
- **标准格式**: `1m`, `5m`, `1h`, `4h`, `1d`, `1w`, `1M`（小写）
- 插件内部自动转换：
  - OKX: `1H`, `1D`
  - Binance: `1h`, `1d`
  - Bybit: `60`, `D`
  - Coinbase: `3600`, `86400`

### 时间戳格式
- **标准格式**: Unix 秒级时间戳
- 前端 ↔ API：毫秒
- API ↔ 插件：秒
- 插件内部自动转换为数据源格式

## API 端点

### 1. 获取所有数据源列表

```http
GET /api/sources/
```

**响应示例**:
```json
{
  "code": 0,
  "total": 6,
  "data": {
    "okx": {
      "metadata": {
        "name": "okx",
        "display_name": "OKX 交易所",
        "description": "全球领先的数字资产交易平台",
        "source_type": "exchange",
        "plugin_version": "2.0.0",
        "is_active": true
      },
      "capability": {
        "supports_candlesticks": true,
        "candlestick_granularities": [
          "1m", "3m", "5m", "15m", "30m",
          "1h", "2h", "4h", "6h", "12h",
          "1d", "1w", "1M"
        ],
        "candlestick_limit": 300,
        "supports_ticker": true,
        "supported_symbols": [
          "BTCUSDT", "ETHUSDT", "BNBUSDT",
          "XRPUSDT", "ADAUSDT", "SOLUSDT"
        ],
        "symbol_format": "BTCUSDT",
        "has_rate_limit": true,
        "rate_limit_per_minute": 600
      }
    },
    "binance": {
      // ... 类似结构
    }
  }
}
```

### 2. 获取单个数据源详情

```http
GET /api/sources/{source_name}/
```

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "name": "okx",
    "metadata": { /* ... */ },
    "capability": { /* ... */ },
    "documentation": "# OKX 数据源文档\n..."
  }
}
```

### 3. 获取行情数据

```http
GET /api/ticker/?symbol=BTCUSDT&source=okx
```

**参数**:
- `symbol`: 交易对（标准格式，如 `BTCUSDT`）
- `source`: 数据源名称（如 `okx`, `binance`）

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "inst_id": "BTCUSDT",
    "last": 91960.90,
    "bid": 91960.80,
    "ask": 91961.00,
    "high_24h": 93612.00,
    "low_24h": 90887.60,
    "change_24h": -1091.10,
    "change_24h_pct": -1.05
  },
  "symbol": "BTCUSDT",
  "source": "okx"
}
```

### 4. 获取K线数据

```http
GET /api/candlesticks/?symbol=BTCUSDT&bar=1h&limit=100&source=okx
```

**参数**:
- `symbol`: 交易对（标准格式）
- `bar`: 时间粒度（标准格式）
- `limit`: 返回条数（默认 100）
- `source`: 数据源名称
- `before`: 获取此时间戳之前的数据（毫秒，可选）
- `after`: 获取此时间戳之后的数据（毫秒，可选）

**响应示例**:
```json
{
  "code": 0,
  "data": [
    {
      "time": 1733414400,
      "open": 91950.0,
      "high": 91980.0,
      "low": 91920.0,
      "close": 91960.0,
      "volume": 123.45
    }
  ],
  "symbol": "BTCUSDT",
  "bar": "1h",
  "source": "okx",
  "cache_info": {
    "count": 100,
    "oldest": 1733050400,
    "newest": 1733414400
  }
}
```

## 前端使用指南

### 1. 初始化时获取数据源能力

```typescript
// 获取所有数据源
const response = await fetch('/api/sources/');
const { data: sources } = await response.json();

// 根据能力筛选
const sourcesWithKline = Object.entries(sources)
  .filter(([_, source]) => source.capability.supports_candlesticks)
  .map(([name, _]) => name);
```

### 2. 动态生成时间粒度选项

```typescript
// 获取特定数据源支持的粒度
const source = sources['okx'];
const availableTimeframes = source.capability.candlestick_granularities;

// 构建下拉选项
const timeframeOptions = availableTimeframes.map(tf => ({
  value: tf,
  label: tf.toUpperCase()
}));
```

### 3. 智能数据源选择

```typescript
function selectBestSource(symbol: string, bar: string): string {
  for (const [name, source] of Object.entries(sources)) {
    const cap = source.capability;
    
    // 检查是否支持该交易对
    if (cap.supported_symbols.length > 0 && 
        !cap.supported_symbols.includes(symbol)) {
      continue;
    }
    
    // 检查是否支持该粒度
    if (!cap.candlestick_granularities.includes(bar)) {
      continue;
    }
    
    // 检查是否支持K线
    if (!cap.supports_candlesticks) {
      continue;
    }
    
    return name;  // 找到合适的数据源
  }
  
  return 'okx';  // 默认使用 OKX
}
```

### 4. 数据源降级策略

```typescript
async function fetchWithFallback(
  symbol: string, 
  bar: string, 
  preferredSource: string
) {
  const fallbackSources = ['okx', 'binance', 'bybit'];
  
  for (const source of [preferredSource, ...fallbackSources]) {
    try {
      const response = await fetch(
        `/api/candlesticks/?symbol=${symbol}&bar=${bar}&source=${source}`
      );
      
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.warn(`数据源 ${source} 失败，尝试下一个`);
    }
  }
  
  throw new Error('所有数据源都不可用');
}
```

## 各数据源能力对比

| 数据源 | K线粒度 | 最大条数 | 限流(/分钟) | 特点 |
|--------|---------|----------|-------------|------|
| OKX | 13种 | 300 | 600 | 全球化，粒度丰富 |
| Binance | 15种 | 1000 | 1200 | 最大条数多，限流高 |
| Bybit | 8种 | 1000 | 120 | 基础粒度，限流低 |
| Coinbase | 7种 | 350 | 10 | 仅 USD，限流严格 |
| CoinGecko | 0种 | - | 50 | 仅行情，无K线 |
| Kraken | 8种 | 720 | 15 | 欧美市场 |

## 错误处理

### 错误码说明

- `code: 0` - 成功
- `code: -1` - 失败，查看 `error` 字段

### 常见错误

```json
{
  "code": -1,
  "error": "OKX API 错误: Instrument ID doesn't exist",
  "symbol": "XXXUSDT",
  "source": "okx"
}
```

**处理建议**:
1. 检查交易对是否在 `supported_symbols` 中
2. 尝试降级到其他数据源
3. 提示用户选择有效的交易对

## 最佳实践

1. **缓存数据源能力信息**
   - 启动时获取一次即可
   - 数据源能力很少变化

2. **优先使用支持交易对多的数据源**
   - Binance: 1000+ 交易对
   - OKX: 500+ 交易对

3. **根据用户地区选择数据源**
   - 中国用户: OKX（需代理）
   - 美国用户: Coinbase
   - 欧洲用户: Kraken

4. **考虑限流限制**
   - 高频刷新: 选择 Binance (1200/分钟)
   - 低频查询: CoinGecko (50/分钟)

5. **实现多数据源冗余**
   - 主数据源 + 2个备用数据源
   - 自动切换机制
