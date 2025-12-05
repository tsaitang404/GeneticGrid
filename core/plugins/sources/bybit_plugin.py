# -*- coding: utf-8 -*-
"""
Bybit 交易所数据源插件
"""

from typing import List, Optional
from datetime import datetime
import logging
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

logger = logging.getLogger(__name__)


class BybitMarketPlugin(MarketDataSourcePlugin):
    """Bybit 交易所数据源插件"""
    
    BASE_URL = "https://api.bybit.com"
    
    def __init__(self):
        self._session = None
        super().__init__()
    
    def _get_metadata(self) -> DataSourceMetadata:
        """获取 Bybit 元数据"""
        return DataSourceMetadata(
            name="bybit",
            display_name="Bybit 交易所",
            description="全球领先的加密货币衍生品交易平台，提供永续合约、期货和现货交易，日交易量数十亿美元",
            source_type=SourceType.EXCHANGE,
            website="https://www.bybit.com",
            api_base_url="https://api.bybit.com",
            plugin_version="1.0.0",
            author="GeneticGrid Team",
            last_updated=datetime(2025, 12, 5),
            is_active=True,
            is_experimental=False,
            requires_proxy=False,  # Bybit 全球可直连
        )
    
    def _get_capability(self) -> Capability:
        """获取 Bybit 能力"""
        return Capability(
            supports_candlesticks=True,
            candlestick_granularities=[
                "1m", "3m", "5m", "15m", "30m",
                "1h", "2h", "4h", "6h", "12h",
                "1d", "1w", "1M"
            ],
            candlestick_limit=1000,  # Bybit 最多返回 1000 条
            candlestick_max_history_days=None,
            supports_ticker=True,
            ticker_update_frequency=1,
            supported_symbols=[],  # 动态获取
            symbol_format="BTCUSDT",  # Bybit 格式
            requires_api_key=False,
            requires_authentication=False,
            requires_proxy=False,
            has_rate_limit=True,
            rate_limit_per_minute=120,
            supports_real_time=False,
            supports_websocket=True,
        )
    
    @property
    def _get_session(self):
        """获取 requests session"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': 'GeneticGrid/1.0'
            })
        return self._session
    
    def _convert_symbol(self, inst_id: str) -> str:
        """将标准格式转换为 Bybit 格式: BTC-USDT -> BTCUSDT"""
        return inst_id.replace("-", "")
    
    def _convert_bar(self, bar: str) -> str:
        """将时间周期转换为 Bybit 格式（分钟数或特殊字符）"""
        mapping = {
            "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30",
            "1h": "60", "2h": "120", "4h": "240", "6h": "360", "12h": "720",
            "1d": "D", "1w": "W", "1M": "M"
        }
        return mapping.get(bar, "60")
    
    def _get_candlesticks_impl(
        self,
        symbol: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
    ) -> List[CandleData]:
        """获取 K线数据"""
        try:
            bybit_symbol = self._convert_symbol(symbol)
            interval = self._convert_bar(bar)
            
            # Bybit V5 API
            url = f"{self.BASE_URL}/v5/market/kline"
            params = {
                "category": "spot",  # 现货
                "symbol": bybit_symbol,
                "interval": interval,
                "limit": min(limit, 1000)
            }
            
            # Bybit 使用 end 参数指定结束时间（毫秒）
            if before:
                params["end"] = before * 1000  # 转为毫秒
            
            response = self._get_session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("retCode") != 0:
                raise PluginError(f"Bybit API 错误: {data.get('retMsg', '未知错误')}")
            
            # Bybit 返回格式: {"result": {"list": [[startTime, open, high, low, close, volume, turnover], ...]}}
            result = data.get("result", {})
            kline_list = result.get("list", [])
            
            if not kline_list:
                raise PluginError("Bybit 返回数据为空")
            
            candles = []
            # Bybit 返回的数据是倒序的（最新的在前），需要反转
            for item in reversed(kline_list):
                candles.append(CandleData(
                    time=int(item[0]) // 1000,  # 毫秒转秒
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5]),
                ))
            
            return candles
            
        except requests.exceptions.Timeout:
            logger.error("Bybit API 连接超时")
            raise PluginError("Bybit API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Bybit 获取 K线数据失败: {e}")
            raise PluginError(f"Bybit 获取 K线数据失败: {e}")
        except Exception as e:
            logger.error(f"Bybit 获取 K线数据失败: {e}")
            raise PluginError(f"Bybit 获取 K线数据失败: {e}")
    
    def _get_ticker_impl(self, symbol: str) -> TickerData:
        """获取行情数据"""
        try:
            bybit_symbol = self._convert_symbol(symbol)
            
            # Bybit V5 API - Tickers
            url = f"{self.BASE_URL}/v5/market/tickers"
            params = {
                "category": "spot",
                "symbol": bybit_symbol
            }
            
            response = self._get_session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("retCode") != 0:
                raise PluginError(f"Bybit API 错误: {data.get('retMsg', '未知错误')}")
            
            # Bybit 返回格式: {"result": {"list": [ticker_data]}}
            result = data.get("result", {})
            ticker_list = result.get("list", [])
            
            if not ticker_list:
                raise PluginError("Bybit 返回数据为空")
            
            ticker = ticker_list[0]
            
            last_price = float(ticker.get("lastPrice", 0))
            high_24h = float(ticker.get("highPrice24h", 0))
            low_24h = float(ticker.get("lowPrice24h", 0))
            prev_price = float(ticker.get("prevPrice24h", 0))
            
            # 计算24h涨跌
            change_24h = last_price - prev_price if prev_price else None
            change_24h_pct = (change_24h / prev_price * 100) if prev_price and change_24h else None
            
            return TickerData(
                inst_id=symbol,
                last=last_price,
                bid=float(ticker.get("bid1Price", 0)) or None,
                ask=float(ticker.get("ask1Price", 0)) or None,
                high_24h=high_24h or None,
                low_24h=low_24h or None,
                change_24h=change_24h,
                change_24h_pct=change_24h_pct,
            )
            
        except requests.exceptions.Timeout:
            logger.error("Bybit API 连接超时")
            raise PluginError("Bybit API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Bybit 获取行情数据失败: {e}")
            raise PluginError(f"Bybit 获取行情数据失败: {e}")
        except Exception as e:
            logger.error(f"Bybit 获取行情数据失败: {e}")
            raise PluginError(f"Bybit 获取行情数据失败: {e}")
