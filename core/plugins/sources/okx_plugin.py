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
    SourceType,
    PluginError,
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
    
    def _normalize_symbol(self, symbol: str) -> str:
        """标准格式 "BTCUSDT" -> OKX 格式 "BTC-USDT" """
        # 解析交易对
        symbol = symbol.upper().replace('-', '').replace('/', '')
        
        # 常见计价币种
        for quote in ['USDT', 'USDC', 'USD', 'BTC', 'ETH']:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}-{quote}"
        
        # 默认：假设后4位是计价币种
        if len(symbol) > 4:
            return f"{symbol[:-4]}-{symbol[-4:]}"
        return symbol
    
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
            requires_api_key=False,
            requires_authentication=False,
            requires_proxy=True,  # 使用代理更稳定
            has_rate_limit=True,
            rate_limit_per_minute=600,
            supports_real_time=True,
            supports_websocket=True,
        )
    
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
            if normalized_bar in {"tick", "1s"}:
                use_realtime = before is None
                candles: List[CandleData] = []

                if use_realtime:
                    candles = self._get_realtime_candles(symbol, limit)
                    if candles:
                        logger.debug(
                            "⚡ 使用 OKX WebSocket 实时缓存 (%s) 返回 %d 条数据",
                            symbol,
                            len(candles)
                        )
                        return candles
                else:
                    logger.debug(
                        "OKX 1s 粒度分页请求改用 REST 接口 (symbol=%s, before=%s)",
                        symbol,
                        before
                    )

                if not candles:
                    if use_realtime:
                        logger.warning(
                            "OKX 实时流在 %.1fs 内未返回数据 (%s, limit=%s)",
                            3.0,
                            symbol,
                            limit
                        )
                    else:
                        logger.info(
                            "OKX 1s 历史数据暂不支持 REST 分页 (symbol=%s)",
                            symbol
                        )
                return candles

            params = {
                "instId": symbol,  # 已转换为 "BTC-USDT" 格式
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
    
    def _get_ticker_impl(self, symbol: str) -> TickerData:
        """获取行情数据的内部实现（已转换为 OKX 格式）
        
        API 文档: https://www.okx.com/docs-v5/en/#rest-api-market-data-get-ticker
        """
        try:
            result = self._request("/market/ticker", {"instId": symbol})
            
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
