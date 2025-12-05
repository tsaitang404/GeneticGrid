# -*- coding: utf-8 -*-
"""
Coinbase 交易所数据源插件
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


class CoinbaseMarketPlugin(MarketDataSourcePlugin):
    """Coinbase 交易所数据源插件
    
    协议实现：
    - 接收标准格式：symbol="BTCUSDT", bar="1h"
    - 内部转换为：symbol="BTC-USD", granularity=3600
    """
    
    BASE_URL = "https://api.exchange.coinbase.com"
    
    def __init__(self):
        self._session = None
        super().__init__()
    
    def _normalize_symbol(self, symbol: str) -> str:
        """标准格式 "BTCUSDT" -> Coinbase 格式 "BTC-USD" """
        symbol = symbol.upper().replace('-', '').replace('/', '')
        
        # Coinbase 只支持 USD，不支持 USDT
        for quote in ['USDT', 'USDC']:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}-USD"
        
        if symbol.endswith('USD'):
            base = symbol[:-3]
            return f"{base}-USD"
        
        # 默认：假设后4位是计价币种，改为 USD
        if len(symbol) > 4:
            return f"{symbol[:-4]}-USD"
        return symbol
    
    def _get_metadata(self) -> DataSourceMetadata:
        """获取 Coinbase 元数据"""
        return DataSourceMetadata(
            name="coinbase",
            display_name="Coinbase 交易所",
            description="美国领先的数字资产交易平台，提供现货和期货交易，支持 100+ 种加密资产",
            source_type=SourceType.EXCHANGE,
            website="https://www.coinbase.com",
            api_base_url="https://api.exchange.coinbase.com",
            plugin_version="1.0.0",
            author="GeneticGrid Team",
            last_updated=datetime(2025, 1, 5),
            is_active=True,
            is_experimental=False,
            requires_proxy=False,  # Coinbase 全球可直连
        )
    
    def _get_capability(self) -> Capability:
        """获取 Coinbase 能力"""
        return Capability(
            supports_candlesticks=True,
            candlestick_granularities=[
                "1m", "5m", "15m", "1h", "4h", "1d", "1w"  # Coinbase 支持的粒度
            ],
            candlestick_limit=350,
            candlestick_max_history_days=None,
            supports_ticker=True,
            ticker_update_frequency=1,
            supported_symbols=[],  # 动态获取
            symbol_format="BASE-USD",  # Coinbase 格式
            requires_api_key=False,
            requires_authentication=False,
            requires_proxy=False,  # Coinbase 全球可直连
            has_rate_limit=True,
            rate_limit_per_minute=10,
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
        """将标准格式转换为 Coinbase 格式: BTC-USDT -> BTC-USD"""
        # Coinbase 使用 USD 而不是 USDT
        return inst_id.replace('USDT', 'USD')
    
    def _convert_bar(self, bar: str) -> int:
        """将时间周期转换为 Coinbase 格式（秒）"""
        mapping = {
            "1m": 60, "5m": 300, "15m": 900,
            "1h": 3600, "1H": 3600,
            "4h": 14400, "4H": 14400,
            "1d": 86400, "1D": 86400,
            "1w": 604800, "1W": 604800,
        }
        return mapping.get(bar, 3600)
    
    def _get_candlesticks_impl(
        self,
        symbol: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
    ) -> List[CandleData]:
        """获取 K线数据"""
        try:
            coinbase_symbol = self._convert_symbol(symbol)
            granularity = self._convert_bar(bar)
            
            # Coinbase Pro API
            url = f"{self.BASE_URL}/products/{coinbase_symbol}/candles"
            params = {
                "granularity": granularity,
            }
            
            response = self._get_session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                raise PluginError("Coinbase 返回数据为空")
            
            # Coinbase 返回格式: [[time, low, high, open, close, volume], ...]
            # 数据是倒序的（最新的在前）
            candles = []
            for item in reversed(data[:limit]):
                candles.append(CandleData(
                    time=int(item[0]),  # Unix timestamp
                    open=float(item[3]),
                    high=float(item[2]),
                    low=float(item[1]),
                    close=float(item[4]),
                    volume=float(item[5]),
                ))
            
            return candles
            
        except requests.exceptions.Timeout:
            logger.error("Coinbase API 连接超时")
            raise PluginError("Coinbase API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Coinbase 获取 K线数据失败: {e}")
            raise PluginError(f"Coinbase 获取 K线数据失败: {e}")
        except Exception as e:
            logger.error(f"Coinbase 获取 K线数据失败: {e}")
            raise PluginError(f"Coinbase 获取 K线数据失败: {e}")
    
    def _get_ticker_impl(self, symbol: str) -> TickerData:
        """获取行情数据"""
        try:
            coinbase_symbol = self._convert_symbol(symbol)
            
            # Coinbase Pro API - Ticker
            url = f"{self.BASE_URL}/products/{coinbase_symbol}/ticker"
            
            response = self._get_session.get(url, timeout=10)
            response.raise_for_status()
            ticker = response.json()
            
            # 获取 24h 统计数据
            stats_url = f"{self.BASE_URL}/products/{coinbase_symbol}/stats"
            stats_response = self._get_session.get(stats_url, timeout=10)
            stats_response.raise_for_status()
            stats = stats_response.json()
            
            last_price = float(ticker.get('price', 0))
            open_24h = float(stats.get('open', 0))
            
            # 计算24h涨跌
            change_24h = last_price - open_24h if open_24h else None
            change_24h_pct = (change_24h / open_24h * 100) if open_24h and change_24h else None
            
            return TickerData(
                inst_id=symbol,
                last=last_price,
                bid=float(ticker.get('bid', 0)) or None,
                ask=float(ticker.get('ask', 0)) or None,
                high_24h=float(stats.get('high', 0)) or None,
                low_24h=float(stats.get('low', 0)) or None,
                change_24h=change_24h,
                change_24h_pct=change_24h_pct,
            )
            
        except requests.exceptions.Timeout:
            logger.error("Coinbase API 连接超时")
            raise PluginError("Coinbase API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Coinbase 获取行情数据失败: {e}")
            raise PluginError(f"Coinbase 获取行情数据失败: {e}")
        except Exception as e:
            logger.error(f"Coinbase 获取行情数据失败: {e}")
            raise PluginError(f"Coinbase 获取行情数据失败: {e}")
