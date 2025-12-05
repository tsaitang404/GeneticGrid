# -*- coding: utf-8 -*-
"""
币安交易所数据源插件
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


class BinanceMarketPlugin(MarketDataSourcePlugin):
    """币安交易所数据源插件"""
    
    BASE_URL = "https://api.binance.com"
    
    def __init__(self):
        self._session = None
        super().__init__()
    
    def _get_metadata(self) -> DataSourceMetadata:
        """获取币安元数据"""
        return DataSourceMetadata(
            name="binance",
            display_name="币安交易所",
            description="全球最大的加密货币交易平台，提供现货、合约、期权等多种交易产品，日交易量超过 300 亿美元",
            source_type=SourceType.EXCHANGE,
            website="https://www.binance.com",
            api_base_url="https://api.binance.com",
            plugin_version="2.0.0",
            author="GeneticGrid Team",
            last_updated=datetime(2025, 12, 5),
            is_active=True,
            is_experimental=False,
            requires_proxy=False,  # 币安全球可直连
        )
    
    def _get_capability(self) -> Capability:
        """获取币安能力"""
        return Capability(
            supports_candlesticks=True,
            candlestick_granularities=[
                "1m", "3m", "5m", "15m", "30m",
                "1h", "2h", "4h", "6h", "12h",
                "1d", "3d", "1w", "1M"
            ],
            candlestick_limit=1000,  # Binance 最多返回 1000 条
            candlestick_max_history_days=None,
            supports_ticker=True,
            ticker_update_frequency=1,
            supported_symbols=[
                # 主流 USDT 交易对
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
                "SOLUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
                "AVAXUSDT", "LINKUSDT", "ATOMUSDT", "UNIUSDT", "ETCUSDT",
                "SHIBUSDT", "TRXUSDT", "BCHUSDT", "NEARUSDT", "APTUSDT",
                # Binance 支持 1000+ 交易对
            ],
            symbol_format="BTCUSDT",  # 币安格式
            requires_api_key=False,
            requires_authentication=False,
            requires_proxy=False,
            has_rate_limit=True,
            rate_limit_per_minute=1200,
            supports_real_time=False,
            supports_websocket=True,
        )
    
    @property
    def _get_session(self):
        """获取 requests session"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': 'GeneticGrid/2.0'
            })
        return self._session
    
    def _convert_symbol(self, inst_id: str) -> str:
        """将标准格式转换为 Binance 格式: BTC-USDT -> BTCUSDT"""
        return inst_id.replace("-", "")
    
    def _convert_bar(self, bar: str) -> str:
        """将时间周期转换为 Binance 格式"""
        mapping = {
            "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "12h": "12h",
            "1d": "1d", "3d": "3d", "1w": "1w", "1M": "1M"
        }
        return mapping.get(bar, "1h")
    
    def _get_candlesticks_impl(
        self,
        symbol: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
    ) -> List[CandleData]:
        """获取 K线数据"""
        try:
            binance_symbol = self._convert_symbol(symbol)
            interval = self._convert_bar(bar)
            
            url = f"{self.BASE_URL}/api/v3/klines"
            params = {
                "symbol": binance_symbol,
                "interval": interval,
                "limit": min(limit, 1000)
            }
            
            # Binance 使用 endTime 参数（毫秒）
            if before:
                params["endTime"] = before * 1000
            
            response = self._get_session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                raise PluginError("Binance 返回数据为空")
            
            candles = []
            for item in data:
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
            logger.error("Binance API 连接超时")
            raise PluginError("Binance API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance 获取 K线数据失败: {e}")
            raise PluginError(f"Binance API 网络错误: {e}")
        except Exception as e:
            logger.error(f"Binance 获取 K线数据失败: {e}")
            raise PluginError(f"Binance 获取 K线数据失败: {e}")
    
    def _get_ticker_impl(self, symbol: str) -> TickerData:
        """获取行情数据"""
        try:
            binance_symbol = self._convert_symbol(symbol)
            
            url = f"{self.BASE_URL}/api/v3/ticker/24hr"
            params = {"symbol": binance_symbol}
            
            response = self._get_session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            last = float(data['lastPrice'])
            open_price = float(data['openPrice'])
            
            # 计算24h涨跌
            change_24h = last - open_price
            change_24h_pct = (change_24h / open_price * 100) if open_price else None
            
            return TickerData(
                inst_id=symbol,
                last=last,
                bid=float(data.get('bidPrice', 0)) or None,
                ask=float(data.get('askPrice', 0)) or None,
                high_24h=float(data.get('highPrice', 0)) or None,
                low_24h=float(data.get('lowPrice', 0)) or None,
                change_24h=change_24h,
                change_24h_pct=change_24h_pct,
            )
            
        except requests.exceptions.Timeout:
            logger.error("Binance API 连接超时")
            raise PluginError("Binance API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance 获取行情数据失败: {e}")
            raise PluginError(f"Binance API 网络错误: {e}")
        except Exception as e:
            logger.error(f"Binance 获取行情数据失败: {e}")
            raise PluginError(f"Binance 获取行情数据失败: {e}")
