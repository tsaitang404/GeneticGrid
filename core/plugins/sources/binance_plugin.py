# -*- coding: utf-8 -*-
"""
币安交易所数据源插件
"""

from typing import List, Optional
from datetime import datetime
import logging

from ..base import (
    MarketDataSourcePlugin,
    DataSourceMetadata,
    Capability,
    CandleData,
    TickerData,
    SourceType,
    PluginError,
)
from ..proxy_injector import inject_proxy_to_service
from core import services as legacy_services

logger = logging.getLogger(__name__)


class BinanceMarketPlugin(MarketDataSourcePlugin):
    """币安交易所数据源插件"""
    
    def __init__(self):
        self._legacy_service = None
        super().__init__()
    
    def _get_metadata(self) -> DataSourceMetadata:
        """获取币安元数据"""
        return DataSourceMetadata(
            name="binance",
            display_name="币安交易所",
            description="全球最大的数字资产交易平台，支持 500+ 交易对，交易量全球领先",
            source_type=SourceType.EXCHANGE,
            website="https://www.binance.com",
            api_base_url="https://api.binance.com/api",
            plugin_version="1.0.0",
            author="GeneticGrid Team",
            last_updated=datetime(2025, 1, 5),
            is_active=True,
            is_experimental=False,
            requires_proxy=False,  # 币安全球可直连
        )
    
    def _get_capability(self) -> Capability:
        """获取币安能力"""
        return Capability(
            supports_candlesticks=True,
            candlestick_granularities=[
                "1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"
            ],
            candlestick_limit=1000,
            candlestick_max_history_days=None,  # 无限制
            supports_ticker=True,
            ticker_update_frequency=1,
            supported_symbols=[],  # 动态获取
            symbol_format="BTCUSDT",  # 币安格式
            requires_api_key=False,
            requires_authentication=False,
            requires_proxy=False,  # 币安全球可直连
            has_rate_limit=True,
            rate_limit_per_minute=1200,
            supports_real_time=False,
            supports_websocket=True,
        )
    
    @property
    def _service(self):
        """延迟加载旧服务并注入代理"""
        if self._legacy_service is None:
            self._legacy_service = legacy_services.BinanceMarketService()
            # 根据元数据配置注入代理
            inject_proxy_to_service(self._legacy_service, self._metadata.requires_proxy)
        return self._legacy_service
    
    def get_candlesticks(
        self,
        symbol: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
    ) -> List[CandleData]:
        """获取 K线数据"""
        try:
            response = self._service.get_candlesticks(
                inst_id=symbol,
                bar=bar,
                limit=min(limit, 1000),
            )
            
            candles = []
            for item in response:
                candles.append(CandleData(
                    time=int(item['time']),  # 旧服务已转为秒
                    open=float(item['open']),
                    high=float(item['high']),
                    low=float(item['low']),
                    close=float(item['close']),
                    volume=float(item['volume']),
                ))
            return candles
        except Exception as e:
            logger.error(f"币安获取 K线数据失败: {e}")
            raise PluginError(f"币安获取 K线数据失败: {e}")
    
    def get_ticker(self, symbol: str) -> TickerData:
        """获取行情数据"""
        try:
            response = self._service.get_ticker(inst_id=symbol)
            
            return TickerData(
                inst_id=symbol,
                last=float(response['last']),
                bid=float(response.get('bid', 0)) or None,
                ask=float(response.get('ask', 0)) or None,
                high_24h=float(response.get('high_24h', 0)) or None,
                low_24h=float(response.get('low_24h', 0)) or None,
                change_24h=float(response.get('change_24h', 0)) or None,
                change_24h_pct=float(response.get('change_24h_pct', 0)) or None,
            )
        except Exception as e:
            logger.error(f"币安获取行情数据失败: {e}")
            raise PluginError(f"币安获取行情数据失败: {e}")
