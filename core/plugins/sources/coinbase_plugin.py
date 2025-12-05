# -*- coding: utf-8 -*-
"""
Coinbase 交易所数据源插件
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


class CoinbaseMarketPlugin(MarketDataSourcePlugin):
    """Coinbase 交易所数据源插件"""
    
    def __init__(self):
        self._legacy_service = None
        super().__init__()
    
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
    def _service(self):
        """延迟加载旧服务并注入代理"""
        if self._legacy_service is None:
            self._legacy_service = legacy_services.CoinbaseMarketService()
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
                limit=min(limit, 350),
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
            logger.error(f"Coinbase 获取 K线数据失败: {e}")
            raise PluginError(f"Coinbase 获取 K线数据失败: {e}")
    
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
            logger.error(f"Coinbase 获取行情数据失败: {e}")
            raise PluginError(f"Coinbase 获取行情数据失败: {e}")
