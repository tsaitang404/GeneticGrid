# -*- coding: utf-8 -*-
"""
OKX 交易所数据源插件 - 使用 REST API
"""

from typing import List, Optional
from datetime import datetime
import logging
import time
import requests

from ..base import (
    MarketDataSourcePlugin,
    DataSourceMetadata,
    Capability,
    CandleData,
    TickerData,
    FundingRateData,
    ContractBasisData,
    SourceType,
    PluginError,
    SymbolMode,
)
from .okx_stream import get_realtime_manager as get_okx_realtime_manager

logger = logging.getLogger(__name__)


class OKXMarketPlugin(MarketDataSourcePlugin):
    """OKX 交易所数据源插件 - 直接使用 REST API
    
    协议实现：
    - 接收标准格式：symbol="BTCUSDT", bar="1h", timestamp=秒
    - 内部转换为：symbol="BTC-USDT", bar="1H", timestamp=毫秒
    """
    
    BASE_URL = "https://www.okx.com/api/v5"
    
    def __init__(self):
        self._realtime = get_okx_realtime_manager()
        super().__init__()

    def _get_realtime_candles(
        self,
        inst_id: str,
        limit: int,
        wait_timeout: float = 3.0,
        poll_interval: float = 0.25,
    ) -> List[CandleData]:
        """从 WebSocket 缓冲区获取 1s K 线，必要时短暂等待以填充数据"""
        if not self._realtime.enabled:
            logger.warning("OKX 实时流不可用（websocket-client 未安装）")
            return []

        deadline = time.time() + max(wait_timeout, 0.0)
        fetch_size = min(max(limit * 2, limit + 100), 7200)
        candles: List[CandleData] = []

        while True:
            candles = self._realtime.get_latest_candles(inst_id, "1s", fetch_size)
            if candles or time.time() >= deadline:
                break
            time.sleep(poll_interval)

        if candles:
            return candles[-limit:]

        logger.warning("OKX 实时流在 %.1fs 内未返回数据 (%s, limit=%s)", wait_timeout, inst_id, limit)
        return []
    
    def _normalize_symbol(
        self,
        symbol: str,
        mode: str = SymbolMode.SPOT.value,
    ) -> str:
        """标准格式 "BTCUSDT" -> OKX 格式 "BTC-USDT" (合约附加 -SWAP)"""
        normalized_mode = (mode or SymbolMode.SPOT.value).lower()

        # 解析交易对
        symbol = symbol.upper().replace('-', '').replace('/', '')
        formatted = symbol

        # 常见计价币种
        for quote in ['USDT', 'USDC', 'USD', 'BTC', 'ETH']:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                formatted = f"{base}-{quote}"
                break
        else:
            # 默认：假设后4位是计价币种
            if len(symbol) > 4:
                formatted = f"{symbol[:-4]}-{symbol[-4:]}"

        if normalized_mode == SymbolMode.CONTRACT.value:
            return self._resolve_contract_inst_id(formatted)
        return formatted
    
    def _normalize_granularity(self, bar: str) -> str:
        """标准格式 "1h" -> OKX 格式 "1H" """
        mapping = {
            "tick": "1s",
            "1s": "1s",
            "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "12h": "12H",
            "1d": "1D", "3d": "3D", "1w": "1W", "1M": "1M",
        }
        return mapping.get(bar, bar)
    
    def _normalize_timestamp(self, timestamp: Optional[int]) -> Optional[int]:
        """秒 -> 毫秒"""
        return timestamp * 1000 if timestamp else None
    
    def _denormalize_timestamp(self, timestamp: int) -> int:
        """毫秒 -> 秒"""
        return timestamp // 1000 if timestamp > 10**10 else timestamp
    
    def _get_metadata(self) -> DataSourceMetadata:
        """获取 OKX 元数据"""
        return DataSourceMetadata(
            name="okx",
            display_name="OKX 交易所",
            description="全球领先的数字资产交易平台，支持现货、期货、永续合约等多种交易产品",
            source_type=SourceType.EXCHANGE,
            website="https://www.okx.com",
            api_base_url=self.BASE_URL,
            plugin_version="2.0.0",
            author="GeneticGrid Team",
            last_updated=datetime(2025, 12, 5),
            is_active=True,
            is_experimental=False,
            requires_proxy=True,  # 使用代理更稳定
        )
    
    def _get_capability(self) -> Capability:
        """获取 OKX 能力"""
        return Capability(
            supports_candlesticks=True,
            candlestick_granularities=[
                "tick",
                "1s",
                "1m", "3m", "5m", "15m", "30m",
                "1h", "2h", "4h", "6h", "12h",
                "1d", "3d", "1w", "1M"
            ],
            candlestick_limit=300,
            candlestick_max_history_days=None,  # 无限制
            supports_ticker=True,
            ticker_update_frequency=1,
            supported_symbols=[
                # 主流币对
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
                "SOLUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
                "AVAXUSDT", "LINKUSDT", "ATOMUSDT", "UNIUSDT", "ETCUSDT",
                # 更多交易对可通过 OKX API 动态获取
            ],
            symbol_format="BTCUSDT",  # 标准格式
            symbol_modes=[SymbolMode.SPOT.value, SymbolMode.CONTRACT.value],
            requires_api_key=False,
            requires_authentication=False,
            requires_proxy=True,  # 使用代理更稳定
            has_rate_limit=True,
            rate_limit_per_minute=600,
            supports_real_time=True,
            supports_websocket=True,
            supports_funding_rate=True,
            funding_rate_interval_hours=8,
            funding_rate_quote_currency=None,
            supports_contract_basis=True,
            contract_basis_types=["perpetual"],
            contract_basis_tenors=["perpetual"],
        )

    def _parse_quote_currency(self, inst_id: str) -> Optional[str]:
        parts = inst_id.split('-')
        if len(parts) >= 2:
            return parts[1]
        return None

    def _resolve_contract_inst_id(
        self,
        symbol: str,
        contract_type: str = "perpetual",
        tenor: Optional[str] = None,
    ) -> str:
        ctype = (contract_type or "perpetual").lower()
        if ctype in {"perpetual", "swap"}:
            if symbol.endswith("-SWAP"):
                return symbol
            return f"{symbol}-SWAP"
        raise PluginError(f"OKX 暂不支持合约类型: {contract_type}")
    
    def _convert_bar(self, bar: str) -> str:
        """已废弃：使用 _normalize_granularity 代替"""
        return self._normalize_granularity(bar)
    
    def _get_proxies(self) -> dict:
        """获取代理配置"""
        try:
            from core.proxy_config import get_proxy
            proxy = get_proxy()
            if proxy:
                return {'http': proxy, 'https': proxy}
        except Exception as e:
            logger.warning(f"获取代理配置失败: {e}")
        return {}
    
    def _request(self, endpoint: str, params: dict = None, timeout: int = 30) -> dict:
        """发送 HTTP 请求到 OKX API"""
        url = f"{self.BASE_URL}{endpoint}"
        proxies = self._get_proxies()
        
        try:
            response = requests.get(
                url,
                params=params,
                proxies=proxies,
                timeout=timeout,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise PluginError(f"OKX API 请求超时（{timeout}秒）")
        except requests.exceptions.RequestException as e:
            raise PluginError(f"OKX API 请求失败: {str(e)}")
    
    def _get_candlesticks_impl(
        self,
        symbol: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
        mode: str = SymbolMode.SPOT.value,
    ) -> List[CandleData]:
        """获取 K线数据的内部实现（已转换为 OKX 格式）
        
        API 文档: https://www.okx.com/docs-v5/en/#rest-api-market-data-get-candlesticks
        
        OKX API 参数说明：
        - 返回数据是倒序的（最新在前，最旧在后）
        - before: 请求此bar时间戳之前的分页内容（用于向后翻页，获取更晚的数据）
        - after: 请求此bar时间戳之后的分页内容（用于向前翻页，获取更早的数据）
        
        注意：OKX 的 before/after 是分页参数，与时间方向相反！
        - 要获取历史数据（更早），使用 after 参数
        - 要获取更新数据（更晚），使用 before 参数
        """
        try:
            normalized_bar = bar.lower()
            inst_id = (
                self._resolve_contract_inst_id(symbol)
                if mode == SymbolMode.CONTRACT.value
                else symbol
            )
            if normalized_bar in {"tick", "1s"}:
                use_realtime = (
                    before is None
                    and mode == SymbolMode.SPOT.value
                )
                candles: List[CandleData] = []

                if use_realtime:
                    candles = self._get_realtime_candles(inst_id, limit)
                    if candles:
                        logger.debug(
                            "⚡ 使用 OKX WebSocket 实时缓存 (%s) 返回 %d 条数据",
                            inst_id,
                            len(candles)
                        )
                        return candles
                else:
                        logger.debug(
                            "OKX 1s 粒度分页请求改用 REST 接口 (symbol=%s, before=%s)",
                            inst_id,
                            before
                        )

                if not candles:
                    if use_realtime:
                        logger.warning(
                            "OKX 实时流在 %.1fs 内未返回数据 (%s, limit=%s)",
                            3.0,
                            inst_id,
                            limit
                        )
                    else:
                        logger.info(
                            "OKX 1s 历史数据暂不支持 REST 分页 (symbol=%s)",
                            inst_id
                        )
                return candles

            params = {
                "instId": inst_id,  # 已转换为 "BTC-USDT" 或带 SWAP 的格式
                "bar": bar,        # 已转换为 "1H" 格式
                "limit": str(min(limit, 300))
            }
            if before:
                # before 参数用于获取历史数据，所以实际应该使用 OKX 的 after 参数
                # before 参数已在 _normalize_timestamp 中转换为毫秒
                params["after"] = str(before)
            
            result = self._request("/market/candles", params)
            
            if result.get("code") != "0":
                raise PluginError(f"OKX API 错误: {result.get('msg', '未知错误')}")
            
            data = result.get("data", [])
            if not data:
                return []  # 返回空列表而不是抛出异常
            
            candles = []
            # OKX 返回倒序数据（最新在前），我们反转为正序（最旧在前）
            for item in reversed(data):
                candles.append(CandleData(
                    time=int(item[0]) // 1000,  # 毫秒转秒
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5]),
                ))
            return candles
            
        except PluginError:
            raise
        except Exception as e:
            logger.error(f"OKX 获取 K线数据失败: {e}")
            raise PluginError(f"OKX 获取 K线数据失败: {str(e)}")
    
    def _get_ticker_impl(
        self,
        symbol: str,
        mode: str = SymbolMode.SPOT.value,
    ) -> TickerData:
        """获取行情数据的内部实现（已转换为 OKX 格式）
        
        API 文档: https://www.okx.com/docs-v5/en/#rest-api-market-data-get-ticker
        """
        try:
            inst_id = (
                self._resolve_contract_inst_id(symbol)
                if mode == SymbolMode.CONTRACT.value
                else symbol
            )
            result = self._request("/market/ticker", {"instId": inst_id})
            
            if result.get("code") != "0":
                raise PluginError(f"OKX API 错误: {result.get('msg', '未知错误')}")
            
            data = result.get("data", [])
            if not data:
                raise PluginError("OKX 返回数据为空")
            
            ticker = data[0]
            last = float(ticker.get('last', 0))
            open_24h = float(ticker.get('open24h', 0))
            volume_24h = float(ticker.get('vol24h', 0) or 0)
            volume_24h = volume_24h if volume_24h > 0 else None
        
            # 计算24h涨跌
            change_24h = last - open_24h if open_24h else None
            change_24h_pct = (change_24h / open_24h * 100) if open_24h and change_24h else None
            
            return TickerData(
                inst_id=symbol,
                last=last,
                bid=float(ticker.get('bidPx', 0)) or None,
                ask=float(ticker.get('askPx', 0)) or None,
                high_24h=float(ticker.get('high24h', 0)) or None,
                low_24h=float(ticker.get('low24h', 0)) or None,
                change_24h=change_24h,
                change_24h_pct=change_24h_pct,
                volume_24h=volume_24h,
            )
            
        except PluginError:
            raise
        except Exception as e:
            logger.error(f"OKX 获取行情数据失败: {e}")
            raise PluginError(f"OKX 获取行情数据失败: {str(e)}")

    def _get_funding_rate_impl(self, symbol: str) -> FundingRateData:
        """获取永续合约资金费率"""
        inst_id = self._resolve_contract_inst_id(symbol, "perpetual")
        try:
            result = self._request("/public/funding-rate", {"instId": inst_id})
            if result.get("code") != "0":
                raise PluginError(f"OKX 资金费率接口错误: {result.get('msg', '未知错误')}")
            data = result.get("data", [])
            if not data:
                raise PluginError("OKX 资金费率接口返回空数据")
            item = data[0]
            funding_rate = float(item.get("fundingRate", 0.0))
            predicted = item.get("nextFundingRate")
            predicted_val = float(predicted) if predicted not in (None, "") else None
            timestamp_raw = item.get("fundingTime")
            next_time_raw = item.get("nextFundingTime")
            funding_time = int(timestamp_raw) // 1000 if timestamp_raw else None
            next_time = int(next_time_raw) // 1000 if next_time_raw else None
            quote_ccy = self._parse_quote_currency(inst_id)
            return FundingRateData(
                inst_id=inst_id,
                funding_rate=funding_rate,
                timestamp=funding_time,
                funding_interval_hours=8,
                next_funding_time=next_time,
                predicted_funding_rate=predicted_val,
                index_price=None,
                premium_index=None,
                quote_currency=quote_ccy,
            )
        except PluginError:
            raise
        except Exception as exc:
            logger.error("OKX 获取资金费率失败: %s", exc)
            raise PluginError(f"OKX 获取资金费率失败: {exc}")

    def _get_contract_basis_impl(
        self,
        symbol: str,
        contract_type: str,
        reference_symbol: Optional[str] = None,
        tenor: Optional[str] = None,
    ) -> ContractBasisData:
        inst_id = self._resolve_contract_inst_id(symbol, contract_type, tenor)
        try:
            # 获取合约ticker（包含标记价格）
            contract_result = self._request("/market/ticker", {"instId": inst_id})
            if contract_result.get("code") != "0":
                raise PluginError(f"OKX 合约ticker错误: {contract_result.get('msg', '未知错误')}")
            contract_data = contract_result.get("data", [])
            if not contract_data:
                raise PluginError("OKX 合约ticker返回空数据")
            
            contract_item = contract_data[0]
            # 使用last价格作为合约价格
            contract_price_raw = contract_item.get("last")
            contract_price = float(contract_price_raw) if contract_price_raw not in (None, "") else None
            
            # 获取现货ticker作为参考价格
            # 从inst_id提取基础货币对，如 BTC-USDT-SWAP -> BTC-USDT
            spot_symbol = "-".join(inst_id.split("-")[:2])
            spot_result = self._request("/market/ticker", {"instId": spot_symbol})
            if spot_result.get("code") != "0":
                raise PluginError(f"OKX 现货ticker错误: {spot_result.get('msg', '未知错误')}")
            spot_data = spot_result.get("data", [])
            if not spot_data:
                raise PluginError("OKX 现货ticker返回空数据")
            
            spot_item = spot_data[0]
            reference_price_raw = spot_item.get("last")
            reference_price = float(reference_price_raw) if reference_price_raw not in (None, "") else None
            
            # 计算基差
            if contract_price is not None and reference_price is not None and reference_price != 0:
                basis = contract_price - reference_price
                basis_rate = (basis / reference_price) * 100  # 转为百分比
            else:
                basis = 0.0
                basis_rate = 0.0
            
            timestamp_raw = contract_item.get("ts")
            timestamp = int(timestamp_raw) // 1000 if timestamp_raw else None
            
            # 解析基础货币
            underlying = spot_symbol.split("-")[0]
            quote_ccy = self._parse_quote_currency(inst_id)
            tenor_value = "perpetual" if contract_type.lower() in {"perpetual", "swap"} else tenor
            
            return ContractBasisData(
                inst_id=inst_id,
                contract_type=contract_type,
                basis=basis,
                timestamp=timestamp,
                basis_rate=basis_rate,
                contract_price=contract_price,
                reference_symbol=underlying,
                reference_price=reference_price,
                tenor=tenor_value,
                quote_currency=quote_ccy,
            )
        except PluginError:
            raise
        except Exception as exc:
            logger.error("OKX 获取合约基差失败: %s", exc)
            raise PluginError(f"OKX 获取合约基差失败: {exc}")

    def get_funding_rate_history(self, symbol: str, limit: int = 100) -> List[dict]:
        """获取资金费率历史数据
        
        Args:
            symbol: 交易对 (BTCUSDT格式)
            limit: 返回数据条数，默认100
            
        Returns:
            资金费率历史数据列表
        """
        # 先格式化symbol为OKX格式 (BTC-USDT)
        formatted_symbol = self._normalize_symbol(symbol, SymbolMode.SPOT.value)
        # 然后解析为合约ID (BTC-USDT-SWAP)
        inst_id = self._resolve_contract_inst_id(formatted_symbol, "perpetual")
        
        try:
            result = self._request("/public/funding-rate", {
                "instId": inst_id,
                "limit": str(min(limit, 100))  # OKX限制最多100条
            })
            
            if result.get("code") != "0":
                raise PluginError(f"OKX 资金费率历史接口错误: {result.get('msg', '未知错误')}")
            
            data = result.get("data", [])
            history = []
            
            for item in data:
                funding_rate_raw = item.get("fundingRate")
                funding_rate = float(funding_rate_raw) if funding_rate_raw not in (None, "") else 0.0
                timestamp_raw = item.get("fundingTime")
                timestamp = int(timestamp_raw) // 1000 if timestamp_raw else None
                
                history.append({
                    "timestamp": timestamp,
                    "funding_rate": funding_rate,
                    "inst_id": inst_id
                })
            
            # 按时间排序（从旧到新）
            history.sort(key=lambda x: x["timestamp"] if x["timestamp"] else 0)
            return history
            
        except PluginError:
            raise
        except Exception as exc:
            logger.error("OKX 获取资金费率历史失败: %s", exc)
            raise PluginError(f"OKX 获取资金费率历史失败: {exc}")

    def get_contract_basis_history(
        self, 
        symbol: str, 
        contract_type: str = "perpetual",
        limit: int = 720,
        granularity: str = "1h"
    ) -> List[dict]:
        """获取合约基差历史数据
        
        通过获取K线数据来计算基差历史
        
        Args:
            symbol: 交易对 (BTCUSDT格式)
            contract_type: 合约类型
            limit: 数据条数
            granularity: 时间粒度 (1m, 5m, 1h, 1d等)
            
        Returns:
            基差历史数据列表
        """
        # 先格式化symbol为OKX格式 (BTC-USDT)
        formatted_symbol = self._normalize_symbol(symbol, SymbolMode.SPOT.value)
        # 然后解析为合约ID (BTC-USDT-SWAP)
        inst_id = self._resolve_contract_inst_id(formatted_symbol, contract_type)
        spot_symbol = formatted_symbol  # BTC-USDT
        
        try:
            # 转换粒度为OKX格式
            okx_bar = self._convert_bar(granularity)
            
            # 获取合约K线
            contract_candles_result = self._request("/market/candles", {
                "instId": inst_id,
                "bar": okx_bar,
                "limit": str(min(limit, 1440))  # OKX限制最多1440条
            })
            
            if contract_candles_result.get("code") != "0":
                raise PluginError(f"OKX 合约K线接口错误: {contract_candles_result.get('msg', '未知错误')}")
            
            # 获取现货K线
            spot_candles_result = self._request("/market/candles", {
                "instId": spot_symbol,
                "bar": okx_bar,
                "limit": str(min(limit, 1440))  # OKX限制最多1440条
            })
            
            if spot_candles_result.get("code") != "0":
                raise PluginError(f"OKX 现货K线接口错误: {spot_candles_result.get('msg', '未知错误')}")
            
            contract_candles = contract_candles_result.get("data", [])
            spot_candles = spot_candles_result.get("data", [])
            
            # 构建现货价格字典用于快速查找
            spot_prices = {}
            for candle in spot_candles:
                ts = int(candle[0]) // 1000  # 转为秒
                close_price = float(candle[4])
                spot_prices[ts] = close_price
            
            history = []
            for candle in contract_candles:
                ts = int(candle[0]) // 1000  # 转为秒
                contract_price = float(candle[4])  # 收盘价
                
                # 查找对应的现货价格
                spot_price = spot_prices.get(ts)
                
                if spot_price and spot_price != 0:
                    basis = contract_price - spot_price
                    basis_rate = (basis / spot_price) * 100
                    
                    history.append({
                        "timestamp": ts,
                        "basis": basis,
                        "basis_rate": basis_rate,
                        "contract_price": contract_price,
                        "spot_price": spot_price,
                        "inst_id": inst_id
                    })
            
            # 按时间排序（从旧到新）
            history.sort(key=lambda x: x["timestamp"])
            return history
            
        except PluginError:
            raise
        except Exception as exc:
            logger.error("OKX 获取合约基差历史失败: %s", exc)
            raise PluginError(f"OKX 获取合约基差历史失败: {exc}")

