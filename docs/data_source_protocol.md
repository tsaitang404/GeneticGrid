# 数据源协议规范

## 1. 目标与适用范围
- 统一前端、后端服务与第三方交易所之间的数据格式，降低插件开发成本。
- 保证所有数据源插件都能在不修改前端代码的情况下热插拔。
- 覆盖行情（Ticker）、K 线、资金费率、合约基差等核心衍生品数据。

## 2. 基本术语
| 名称 | 说明 |
| ---- | ---- |
| 标准交易对 | 全大写、无分隔符，例如 `BTCUSDT`。|
| 数据源标识 | `okx`、`binance`、`bybit`、`coinbase`、`kraken`、`coingecko` 等。|
| 交易模式 | `spot`、`contract`，在请求参数 `mode` 中体现。|
| 标准时间粒度 | 使用小写单位，例如 `1s`, `1m`, `5m`, `1h`, `1d`, `1w`, `1M`。|
| 标准时间戳 | Unix 时间戳，毫秒用于 HTTP API，秒用于内部对象。|

## 3. 请求标准化流程
所有前端到服务端的查询都会调用 `ProtocolConverter` 完成以下步骤：
1. **解析交易对** (`parse_symbol`)：拆分出基础币种与计价币种，支持 `BTC-USDT`, `BTC/USDT`, `XBTUSDT` 等格式。
2. **转换交易对** (`to_source_symbol`)：根据数据源配置应用分隔符、特殊映射（如 Kraken: `BTC` -> `XBT`、CoinGecko: `BTC` -> `bitcoin`）。
3. **转换时间粒度** (`to_source_granularity`)：将标准粒度映射为数据源所需的格式。
4. **转换时间戳** (`to_source_timestamp`)：按数据源要求在毫秒与秒之间互转。
5. **组合请求参数** (`normalize_request_params`)：输出统一的参数包，供插件或 HTTP 客户端直接使用。

响应返回后会通过 `normalize_response_data` 将时间戳转回毫秒、并递归处理嵌套结构，保证前端观察到的字段永远是标准格式。

## 4. 时间粒度映射
> 以下表格列出核心数据源的默认映射，具体支持的粒度以各插件 `Capability.candlestick_granularities` 为准。

| 标准粒度 | OKX | Binance | Bybit | Coinbase | Kraken |
| -------- | --- | ------- | ----- | -------- | ------ |
| `1s` | `1s` | `1s` (仅现货) | - | - | - |
| `1m` | `1m` | `1m` | `1` | `60` | `1` |
| `5m` | `5m` | `5m` | `5` | `300` | `5` |
| `15m` | `15m` | `15m` | `15` | `900` | `15` |
| `30m` | `30m` | `30m` | `30` | - | `30` |
| `1h` | `1H` | `1h` | `60` | `3600` | `60` |
| `4h` | `4H` | `4h` | `240` | - | `240` |
| `1d` | `1D` | `1d` | `D` | `86400` | `1440` |
| `1w` | `1W` | `1w` | `W` | - | `10080` |
| `1M` | `1M` | `1M` | `M` | - | - |

注意：
- 合约 API 通常不支持 `1s` 粒度，系统会自动降级为 `1m` 并记录日志。
- 当标准粒度不在映射表内时，`ProtocolConverter` 会回退到原值，插件可继续决定是否聚合或报错。

## 5. 时间戳策略
| 环节 | 单位 | 说明 |
| ---- | ---- | ---- |
| 前端 ↔ Django API | 毫秒 | 方便与浏览器 `Date.now()` 对齐。|
| 插件内部对象 (`CandleData`, `FundingRateData` 等) | 秒 | 统一序列化和缓存键。|
| 数据源实际请求 | 由 `SOURCE_FORMATS[time_unit]` 决定（ms 或 s）。|

`ProtocolConverter.from_source_timestamp` / `to_source_timestamp` 负责在不同单位之间互转，插件无需重复处理。

## 6. 标准数据对象
### 6.1 CandleData
| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `time` | int | Unix 秒级时间戳。|
| `open` / `high` / `low` / `close` | float | K 线四价。|
| `volume` | float | 交易量，以交易所原始口径为准。|

### 6.2 TickerData
| 字段 | 说明 |
| ---- | ---- |
| `inst_id` | 标准交易对。|
| `last` | 最新成交价。|
| `bid` / `ask` | 最优买卖价。|
| `high_24h` / `low_24h` | 24h 最高/最低。|
| `change_24h` / `change_24h_pct` | 24h 涨跌额与涨跌幅。|
| `volume_24h` | 24h 成交量。|

### 6.3 FundingRateData
| 字段 | 说明 |
| ---- | ---- |
| `inst_id` | 合约交易对。|
| `funding_rate` | 当前资金费率，十进制表示，例如 `0.0005 = 0.05%`。|
| `timestamp` | 当前费率生效时间（秒）。|
| `funding_interval_hours` | 结算周期，常见值 8 小时。|
| `next_funding_time` | 下一次结算时间。|
| `predicted_funding_rate` | 预测费率（若数据源提供）。|
| `index_price` / `premium_index` | 指标价格与溢价指数。|
| `quote_currency` | 结算货币，常见为 `USDT`。|

### 6.4 ContractBasisData
| 字段 | 说明 |
| ---- | ---- |
| `inst_id` | 合约交易对。|
| `contract_type` | 例如 `perpetual`, `futures`。|
| `tenor` | 交割合约到期类型，如 `current_quarter`。|
| `basis` | 绝对基差 = 合约价 - 现货价。|
| `basis_rate` | 相对基差 = basis / reference_price。|
| `contract_price` / `reference_price` | 合约与基准价格。|
| `reference_symbol` | 基准标的（通常是现货交易对）。|
| `timestamp` | 数据时间（秒）。|
| `quote_currency` | 计价/结算货币。|

所有数据对象都实现 `to_dict()`，便于序列化与缓存。

## 7. 能力与元数据注册
插件必须实现 `MarketDataSourcePlugin` 抽象方法并返回以下结构：
- `DataSourceMetadata`
  - `name`, `display_name`, `description`
  - `source_type` (`exchange` / `aggregator` / `charting`)
  - `website`, `api_base_url`, `plugin_version`
  - `is_active`, `requires_proxy`, `has_rate_limit`, `rate_limit_per_minute`
- `Capability`
  - `supports_candlesticks`, `candlestick_granularities`, `candlestick_limit`
  - `supports_ticker`, `supported_symbols`, `symbol_modes`
  - `supports_funding_rate`, `funding_rate_interval_hours`, `funding_rate_quote_currency`
  - `supports_contract_basis`, `contract_basis_types`, `contract_basis_tenors`
  - 其他通用字段（实时/WS 支持、是否需要认证等）

系统会在插件初始化时校验粒度列表是否符合 `Granularity.GRANULARITIES`，如不符合会输出警告。

## 8. 参数校验与错误语义
`ProtocolConverter.validate_request` 返回 `(is_valid, error)`：
- 检查数据源是否注册。
- 检查时间粒度是否受支持。
- 校验交易对格式是否可解析。

HTTP API 统一返回：
```json
{ "code": 0, "data": [...], "symbol": "BTCUSDT", "source": "okx" }
```
失败时：
```json
{ "code": -1, "error": "数据源 okx 不支持粒度 7m" }
```

## 9. 插件开发检查清单
1. 继承 `MarketDataSourcePlugin`，实现 `_get_metadata` 与 `_get_capability`。
2. 在 `_get_candlesticks_impl` 中使用 `_normalize_symbol`、`_normalize_granularity`、`_normalize_timestamp` 处理请求。
3. 对不支持的粒度提供降级或明确报错（如合约 `1s` 自动降级为 `1m`）。
4. 返回的所有 `CandleData`/`TickerData`/`FundingRateData`/`ContractBasisData` 必须使用标准格式。
5. 若需要代理/鉴权，在 `_get_proxies` 或请求层统一配置，避免泄露敏感凭据。
6. 在出错时抛出 `PluginError`，框架会统一包装为 API 错误。

## 10. 与缓存及 API 的协同
- K 线与行情数据由 `CandlestickCacheService`、`DerivativeDataCacheService` 等组件按 `source:symbol:mode:bar` 命名隔离。
- 粒度或合约类型发生变化时需要使用独立的缓存键，例如 `basis_history:okx:BTCUSDT:perpetual:5m`。
- 插件只需遵循协议输出标准字段，缓存与视图层就能自动复用。

## 11. 参考文件
- `core/protocol.py`：标准化与映射核心实现。
- `core/plugins/base.py`：数据对象、能力与插件基类定义。
- `docs/DATA_SOURCE_API.md`：面向前端的 API 使用说明（与本规范配套）。
