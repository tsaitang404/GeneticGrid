# 前后端 REST API 协议

本文记录 GeneticGrid 前后端主要 HTTP 接口、请求/响应格式以及 REST 风格符合度评估，便于前端联调与第三方集成。

## 1. 总览
- **Base URL（本地开发）**: `http://localhost:8000`
- **所有接口路径**: `/api/...`
- **协议**: HTTPS/HTTP，默认 JSON 编码（UTF-8）
- **认证**: 当前无鉴权逻辑，内网或代理层负责访问控制
- **时间**: 请求参数使用毫秒时间戳；接口返回值统一为 Unix 秒级时间戳（`time`, `timestamp` 等字段）
- **货币与交易对**: 使用标准大写无分隔符（如 `BTCUSDT`），插件负责与交易所格式互转

## 2. 通用约定

### 2.1 请求
- HTTP `GET` 为主，查询参数形式传递筛选条件
- 常用查询字段：`symbol`, `source`, `mode`, `bar`, `limit`, `before`, `after`, `granularity`, `contract_type`
- `mode` 仅接受 `spot`、`contract`

### 2.2 响应包裹结构
```json
{
  "code": 0,
  "data": { /* 业务字段 */ },
  "symbol": "BTCUSDT",
  "source": "okx"
}
```
- `code = 0` 表示成功；`code = -1` 表示失败，错误原因见 `error`
- HTTP 状态码：
  - 200 成功
  - 400 参数错误/能力不支持
  - 404 数据源不存在
  - 500 插件或服务内部异常

### 2.3 缓存策略
- 通过 `Cache-Control` 显式暴露：
  - 最新行情/基差/资金费率：`max-age=30` 或更短
  - 历史数据：`max-age=300`
  - 最新 K 线：`max-age=5`
- 响应中可包含 `cached: true/false` 和 `cache_info`（`count`, `oldest`, `newest`）辅助前端判断

## 3. 接口清单

| 功能 | 方法 & 路径 | 关键参数 | 说明 |
| ---- | ----------- | -------- | ---- |
| 获取数据源列表 | `GET /api/sources/` | 无 | 返回所有插件的 `metadata` 与 `capability` |
| 获取单个数据源 | `GET /api/sources/{source_name}/` | `source_name` | 附带 markdown 文档与能力信息 |
| 获取全部文档 | `GET /api/sources/documentation/` | 无 | 汇总所有插件文档与 JSON 能力快照 |
| 查看代理状态 | `GET /api/proxy-status/` | 无 | 返回 SOCKS5/HTTP 代理健康状况 |
| 实时行情 | `GET /api/ticker/` | `symbol`, `source`, `mode` | 最新成交、盘口与 24h 统计 |
| K 线 | `GET /api/candlesticks/` | `symbol`, `source`, `mode`, `bar`, `limit`, `before`, `after` | 自动调用缓存+插件拉取所需周期 |
| 当前资金费率 | `GET /api/funding-rate/` | `symbol`, `source` | 仅合约，含预测费率/下一结算时间 |
| 资金费率历史 | `GET /api/funding-rate/history/` | `symbol`, `source`, `limit`, `granularity` | 默认 8h 粒度，返回时间序列 |
| 当前合约基差 | `GET /api/contract-basis/` | `symbol`, `source`, `contract_type` | 返回绝对/相对基差、参考价 |
| 合约基差历史 | `GET /api/contract-basis/history/` | `symbol`, `source`, `contract_type`, `limit`, `granularity` | 支持 1m/5m/1h/1d 等粒度 |

下文对关键接口展开说明。

### 3.1 `/api/ticker/`
- **描述**: 拉取指定数据源最新行情，支持现货与合约模式
- **示例请求**: `/api/ticker/?symbol=BTCUSDT&source=okx&mode=spot`
- **响应字段** (`data`): `inst_id`, `last`, `bid`, `ask`, `high_24h`, `low_24h`, `change_24h`, `change_24h_pct`, `volume_24h`
- **缓存**: `Cache-Control: public, max-age=3`

### 3.2 `/api/candlesticks/`
- **描述**: 标准化 K 线接口，内部自动选择插件、落缓存
- **必填参数**: `symbol`, `bar`, `source`
- **可选参数**: `mode` (默认 `spot`), `limit` (默认 100), `before`, `after`
- **响应字段**:
  - `data`: `CandleData[]` (`time`, `open`, `high`, `low`, `close`, `volume`)
  - `cache_info`: `{count, oldest, newest}`
- **缓存**: 最新 `max-age=5`，历史 `max-age=300`

### 3.3 `/api/funding-rate/`
- **描述**: 返回当前资金费率（仅合约）
- **响应字段**: `funding_rate`, `funding_interval_hours`, `next_funding_time`, `predicted_funding_rate`, `index_price`, `premium_index`, `quote_currency`
- **缓存**: `max-age=30`

### 3.4 `/api/funding-rate/history/`
- **描述**: 资金费率时间序列，默认 8 小时粒度
- **参数**: `symbol`, `source`, `limit`, `granularity`
- **响应**: `data: FundingRateData[]`（仅 `funding_rate`, `timestamp` 等核心字段）

### 3.5 `/api/contract-basis/`
- **描述**: 即时合约基差，包含绝对/相对值与当前合约、现货价格
- **参数**: `symbol`, `source`, `contract_type`
- **响应字段**: `basis`, `basis_rate`, `contract_price`, `reference_price`, `quote_currency`, `timestamp`

### 3.6 `/api/contract-basis/history/`
- **描述**: 合约基差历史曲线，支持粒度与条数控制
- **参数**: `symbol`, `source`, `contract_type`, `limit`, `granularity`
- **缓存**: `max-age=300`，且缓存键包含粒度以避免数据混淆

### 3.7 `/api/sources/` & `/api/sources/{source}/`
- **描述**: 提供插件注册表、能力元数据、限流信息与 doc
- **响应字段**: 
  - `metadata`: `name`, `display_name`, `description`, `source_type`, `plugin_version`, `requires_proxy`, `rate_limit_per_minute`
  - `capability`: 是否支持 K 线/行情/资金费率/基差、支持粒度、最大条数、符号列表等

### 3.8 `/api/proxy-status/`
- **描述**: 辅助诊断代理配置，返回 SOCKS5/HTTP host、端口、可用状态

## 4. REST 风格符合性评估

| REST 要素 | 现状 | 评价 |
| -------- | ---- | ---- |
| **资源路径** | 大部分路径基于名词（`/api/candlesticks`, `/api/sources`），符合 REST 语义；少量含动作的路径（`/api/proxy-status`）但仍可视作资源读取 | ✅ 基本符合 |
| **HTTP 动词** | 当前仅实现 `GET`，无创建/更新语义；对读操作完全符合 | ⚠️ 功能单一（只读场景可接受） |
| **状态码使用** | 200/400/404/500 区分清晰，但错误时仍返回 `code=-1` + 200 的情况极少，大多数错误使用对应 HTTP 状态码 | ✅ 基本符合 |
| **超媒体/自描述** | 响应包裹 `{code,data}`，未提供 HATEOAS 链接，但 REST 中并非硬性要求 | ⚠️ 可选改进 |
| **缓存** | 合理利用 `Cache-Control`，并在包体内暴露 `cache_info` | ✅ 符合 |
| **统一资源标识** | 通过查询参数控制资源视图（symbol/source/bar），不需要额外 RPC 式动作 | ✅ 符合 |
| **错误语义** | 返回统一 `code`/`error` 字段，便于前端解析；仍建议对 4xx/5xx 一律返回非 200 状态码 | ⚠️ 局部改进 |

**结论**: 接口整体保持资源化、无状态、可缓存的特征，已经满足 REST 的核心要求。由于业务仅涉及读取，因此仅提供 `GET` 并不会破坏 REST 原则；若未来扩展写操作，需补充 `POST/PUT/DELETE` 与更丰富的状态码。当前主要改进点是：
1. 遇到参数错误/插件错误时，可直接让 HTTP 状态码和 `code` 保持一致，减少双判逻辑。
2. 对于不支持的粒度/模式，建议返回 400 而非自动降级，以保持资源表现的可预测性。

---
如需扩展，请同步更新本文并保持与 `docs/DATA_SOURCE_API.md`、`core/views.py` 的实现一致。