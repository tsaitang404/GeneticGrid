## OKX 官方 API 摘要

本文件整理了 OKX V5 官方文档中与本项目最相关的市场数据、资金费率与衍生品指标端点，便于插件开发和问题排查。

### 1. 基础信息
- **生产 REST 基址**: `https://www.okx.com`
- **WebSocket**:
	- 公共: `wss://ws.okx.com:8443/ws/v5/public`
	- 私有: `wss://ws.okx.com:8443/ws/v5/private`
- **时间戳**: 所有响应中的 `ts`、`uTime`、`cTime` 等字段均为 Unix 毫秒时间戳（13 位）。
- **服务特点**: 官方文档指出市场数据由多个无状态服务提供，请求之间可能返回不同时间片的数据，属于正常现象。

### 2. 鉴权与环境
- **无需鉴权**: `/api/v5/market/*` 与 `/api/v5/public/*` 属于公共只读端点，可直接访问。
- **需要鉴权**: `/api/v5/account/*`, `/api/v5/trade/*`, `/api/v5/algo/*` 等交易、资产类端点必须携带 API Key、Secret、Passphrase，并遵循账号的账户模式（Spot/Futures/Portfolio）。
- **账户模式**: 交易前需在 Web/App 设置，API 仅读取模式；插件只消费市场数据时无需处理。

### 3. 速率限制 (官方速率 = 每 IP 2 秒窗口)

| 端点 | 速率 | 说明 |
| --- | --- | --- |
| `GET /api/v5/market/tickers` | 20 req/2s | 返回某 `instType` 下的全部合约快照 |
| `GET /api/v5/market/ticker` | 20 req/2s | 单一合约快照 |
| `GET /api/v5/market/books` | 40 req/2s | 传统深度，`sz` 默认 1~400 档 |
| `GET /api/v5/market/candles` | 40 req/2s | 最新 K 线（最多 100 条） |
| `GET /api/v5/market/history-candles` | 20 req/2s | 历史 K 线，含分页 |
| `GET /api/v5/market/trades` | 100 req/2s | 最近成交明细 |
| `GET /api/v5/market/history-trades` | 20 req/2s | 三个月内成交，带分页 |
| `GET /api/v5/market/platform-24-volume` | 2 req/2s | 全站 24h 交易量 |
| `GET /api/v5/public/funding-rate` | 5 req/2s | 最新资金费率（官方说明） |
| `GET /api/v5/public/funding-rate-history` | 5 req/2s | 历史费率（limit≤100） |

> **注意**: 除非文档特别声明，速率以 IP 维度统计；私有/交易端点会改用 UID+IP 组合或 API Key 维度。

### 4. 核心市场数据端点

#### 4.1 综合行情
- `GET /api/v5/market/tickers?instType=SWAP`
	- `instType`: `SPOT`, `MARGIN`, `SWAP`, `FUTURES`, `OPTION`
	- 响应字段：`last`, `bidPx`, `askPx`, `open24h`, `high24h`, `low24h`, `vol24h`, `volCcy24h`, `sodUtc0/8`, `ts`。
- `GET /api/v5/market/ticker?instId=BTC-USDT-SWAP`
	- 用于插件快速拉取单一标的快照或校验交易对有效性。

#### 4.2 深度 (Order Book)
- `GET /api/v5/market/books?instId=BTC-USDT&sz=200`
	- `sz` 取值 1~400，默认为 1；返回 `asks`、`bids`、`ts`。
	- 缺省情况下仅返回最优 1 档，可根据插件需要放大。

#### 4.3 K 线
- `GET /api/v5/market/candles?instId=BTC-USDT&bar=1H&limit=100`
	- `bar` 范围：`1m`, `3m`, `5m`, `15m`, `30m`, `1H`, `2H`, `4H`, `6H`, `12H`, `1D`, `1W`, `1M` 等。
	- 返回格式：`[ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]`。
	- 合约品种 **不支持** `1s` 粒度，如需 1 秒线需自行降级为 `1m`（插件已实现）。

- `GET /api/v5/market/history-candles`
	- 支持 `after` / `before` 分页（毫秒），每次最多 100 条。
	- 适合批量补齐历史窗口，注意请求方向与缓存键保持一致。

#### 4.4 成交 & 24h 体量
- `GET /api/v5/market/trades?instId=BTC-USDT`
	- 字段：`tradeId`, `px`, `sz`, `side`, `ts`, `source`。
- `GET /api/v5/market/history-trades`
	- 仅支持近 3 个月的数据，需要 `before/after` 翻页。
- `GET /api/v5/market/platform-24-volume`
	- 返回 `volUsd`, `volCny`, `ts`，用于全市场概览，不区分品种。

### 5. 衍生品与指标端点

#### 5.1 资金费率
- `GET /api/v5/public/funding-rate?instId=BTC-USDT-SWAP`
	- 字段：`fundingRate`, `nextFundingRate`, `fundingTime`, `nextFundingTime`, `interestRate`, `instId`。
	- 仅适用于永续合约；`fundingRate` 为十进制小数（0.0005 = 0.05%）。
- `GET /api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP&limit=100`
	- 字段：`fundingRate`, `realizedRate`, `fundingTime`, `instId`。
	- 支持 `before/after`，按时间倒序返回，最多 3,000 条（每次 100 条）。

#### 5.2 Premium / Index / 基差相关
- `GET /api/v5/public/premium-index?instId=BTC-USDT-SWAP`
	- 字段：`markPx`, `indexPx`, `lastFundingRate`, `nextFundingRate`, `interestRate`, `premiumRate`。
- `GET /api/v5/market/index-components?index=BTC-USDT`
	- 返回组成该指数的交易所及权重，字段：`symbol`, `exchange`, `weight`, `price`。
- `GET /api/v5/market/mark-price-candles?instId=BTC-USDT-SWAP&bar=5m`
	- 提供标记价格时间序列，可与现货 `candles` 结合推导合约基差。
- 以上数据用于 `ContractBasisData` 的 `contract_price`（取 mark/last）、`reference_price`（取 `indexPx` 或现货价格）。

#### 5.3 其他常用公共数据
- `GET /api/v5/public/instruments?instType=SWAP`
	- 字段：`instId`, `uly`, `ctVal`, `tickSz`, `lotSz`, `maxLmtSz`, `maxMktSz` 等。
	- 用于校验交易对是否存在、拉取最小下单量、粒度信息。
- `GET /api/v5/public/estimated-price?instId=BTC-USD-240628`
	- 提供交割/行权估价，可辅助长周期基差分析。

### 6. 响应结构与分页惯例
- 通用响应：`{ "code": "0", "msg": "", "data": [...] }`，`code != 0` 需读取 `msg`/`sMsg`。
- 分页参数：
	- `before`: 返回早于该 `ts` 的记录。
	- `after`: 返回晚于该 `ts` 的记录。
	- `limit`: 默认 100，部分端点允许 300（以文档为准）。
- 顺序：大多数市场端点按时间倒序返回；若服务端缓存导致乱序，可依 `ts` 自行排序。

### 7. 插件集成要点
1. **符号转换**：OKX 使用 `BTC-USDT`、`ETH-USD-SWAP` 等带连字符格式，插件需通过 `ProtocolConverter` 统一为标准 `BTCUSDT`。
2. **粒度映射**：官方 `bar` 参数大小写混用（`1H`, `1D`），务必维持映射表，特别是永续合约不支持 `1s`。
3. **缓存隔离**：对于资金费率、基差历史，请将 `mode`、`granularity`、`instId` 组合进缓存键，避免跨粒度污染。
4. **速率控制**：公共端点虽为 IP 限流，但云环境常共享出口 IP，应在插件层做节流（例如 35 req/s 全局限额）。
5. **数据一致性**：市场数据存在多服务返回不同快照的情况。在构造基差或资金费率时间序列时，务必根据 `ts` 重新排序后再写入缓存。

更多细节可参考 OKX 官方文档：https://www.okx.com/docs-v5/en/#rest-api-market-data
