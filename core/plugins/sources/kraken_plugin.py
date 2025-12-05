# -*- coding: utf-8 -*-
"""
Kraken 交易所数据源插件
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


class KrakenMarketPlugin(MarketDataSourcePlugin):
    """Kraken 交易所数据源插件"""
    
    BASE_URL = "https://api.kraken.com/0/public"
    
    def __init__(self):
        self._session = None
        super().__init__()
    
    def _get_metadata(self) -> DataSourceMetadata:
        """获取 Kraken 元数据"""
        return DataSourceMetadata(
            name="kraken",
            display_name="Kraken 交易所",
            description="成立于2011年的美国加密货币交易所，以安全性和合规性著称，支持50+加密货币交易",
            source_type=SourceType.EXCHANGE,
            website="https://www.kraken.com",
            api_base_url="https://api.kraken.com/0/public",
            plugin_version="1.0.0",
            author="GeneticGrid Team",
            last_updated=datetime(2025, 12, 5),
            is_active=True,
            is_experimental=False,
            requires_proxy=False,  # Kraken 全球可直连
        )
    
    def _get_capability(self) -> Capability:
        """获取 Kraken 能力"""
        return Capability(
            supports_candlesticks=True,
            candlestick_granularities=[
                "1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"
            ],
            candlestick_limit=720,  # Kraken 最多返回 720 条
            candlestick_max_history_days=None,
            supports_ticker=True,
            ticker_update_frequency=1,
            supported_symbols=[],  # 动态获取
            symbol_format="XBTUSDT",  # Kraken 使用 XBT 代替 BTC
            requires_api_key=False,
            requires_authentication=False,
            requires_proxy=False,
            has_rate_limit=True,
            rate_limit_per_minute=15,  # Kraken 公共API限制较严格
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
        """将标准格式转换为 Kraken 格式: BTC-USDT -> XBTUSDT"""
        # Kraken 使用 XBT 而不是 BTC
        symbol = inst_id.replace("-", "")
        symbol = symbol.replace("BTC", "XBT")
        return symbol
    
    def _convert_bar(self, bar: str) -> int:
        """将时间周期转换为 Kraken 格式（分钟数）"""
        mapping = {
            "1m": 1, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "1H": 60, "4h": 240, "4H": 240,
            "1d": 1440, "1D": 1440, "1w": 10080, "1W": 10080
        }
        return mapping.get(bar, 60)
    
    def get_candlesticks(
        self,
        symbol: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
    ) -> List[CandleData]:
        """获取 K线数据"""
        try:
            kraken_symbol = self._convert_symbol(symbol)
            interval = self._convert_bar(bar)
            
            url = f"{self.BASE_URL}/OHLC"
            params = {
                "pair": kraken_symbol,
                "interval": interval,
            }
            
            # Kraken 的 since 参数是开始时间（Unix秒）
            if before:
                params["since"] = before - (limit * interval * 60)
            
            response = self._get_session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("error") and len(data["error"]) > 0:
                raise PluginError(f"Kraken API 错误: {data['error']}")
            
            # Kraken 返回格式: {pair: [[time, open, high, low, close, vwap, volume, count], ...]}
            result_key = list(data.get("result", {}).keys())[0] if data.get("result") else None
            if not result_key or result_key == "last":
                raise PluginError("Kraken 返回数据为空")
            
            ohlc_data = data["result"][result_key]
            
            candles = []
            for item in ohlc_data[-limit:]:
                candles.append(CandleData(
                    time=int(item[0]),  # 已经是秒
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[6]),
                ))
            
            return candles
            
        except requests.exceptions.Timeout:
            logger.error("Kraken API 连接超时")
            raise PluginError("Kraken API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Kraken 获取 K线数据失败: {e}")
            raise PluginError(f"Kraken 获取 K线数据失败: {e}")
        except Exception as e:
            logger.error(f"Kraken 获取 K线数据失败: {e}")
            raise PluginError(f"Kraken 获取 K线数据失败: {e}")
    
    def get_ticker(self, symbol: str) -> TickerData:
        """获取行情数据"""
        try:
            kraken_symbol = self._convert_symbol(symbol)
            
            url = f"{self.BASE_URL}/Ticker"
            params = {"pair": kraken_symbol}
            
            response = self._get_session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("error") and len(data["error"]) > 0:
                raise PluginError(f"Kraken API 错误: {data['error']}")
            
            # Kraken 返回格式: {pair: {a: [ask, ...], b: [bid, ...], c: [last, ...], h: [high, high24h], l: [low, low24h], o: open, ...}}
            result_key = list(data.get("result", {}).keys())[0] if data.get("result") else None
            if not result_key:
                raise PluginError("Kraken 返回数据为空")
            
            ticker = data["result"][result_key]
            
            last_price = float(ticker["c"][0])
            open_price = float(ticker["o"])
            
            # 计算24h涨跌
            change_24h = last_price - open_price
            change_24h_pct = (change_24h / open_price * 100) if open_price else None
            
            return TickerData(
                inst_id=symbol,
                last=last_price,
                bid=float(ticker["b"][0]) if ticker.get("b") else None,
                ask=float(ticker["a"][0]) if ticker.get("a") else None,
                high_24h=float(ticker["h"][1]) if ticker.get("h") else None,
                low_24h=float(ticker["l"][1]) if ticker.get("l") else None,
                change_24h=change_24h,
                change_24h_pct=change_24h_pct,
            )
            
        except requests.exceptions.Timeout:
            logger.error("Kraken API 连接超时")
            raise PluginError("Kraken API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Kraken 获取行情数据失败: {e}")
            raise PluginError(f"Kraken 获取行情数据失败: {e}")
        except Exception as e:
            logger.error(f"Kraken 获取行情数据失败: {e}")
            raise PluginError(f"Kraken 获取行情数据失败: {e}")
