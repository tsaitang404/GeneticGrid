# -*- coding: utf-8 -*-
"""
CoinGecko 数据聚合器插件
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


class CoinGeckoMarketPlugin(MarketDataSourcePlugin):
    """CoinGecko 数据聚合器插件"""
    
    def __init__(self):
        self._legacy_service = None
        super().__init__()
    
    def _get_metadata(self) -> DataSourceMetadata:
        """获取 CoinGecko 元数据"""
        return DataSourceMetadata(
            name="coingecko",
            display_name="CoinGecko 聚合器",
            description="免费的加密资产数据聚合平台，汇聚全球多个交易所的实时数据和历史价格",
            source_type=SourceType.AGGREGATOR,
            website="https://www.coingecko.com",
            api_base_url="https://api.coingecko.com/api/v3",
            plugin_version="1.0.0",
            author="GeneticGrid Team",
            last_updated=datetime(2025, 1, 5),
            is_active=True,
            is_experimental=False,
            requires_proxy=False,  # CoinGecko 全球可直连
        )
    
    def _get_capability(self) -> Capability:
        """获取 CoinGecko 能力"""
        return Capability(
            supports_candlesticks=False,  # CoinGecko 不提供 K线数据
            candlestick_granularities=[],
            supports_ticker=True,
            ticker_update_frequency=60,
            supported_symbols=[
                "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "DOGE-USDT",
                "ADA-USDT", "AVAX-USDT", "LINK-USDT"
            ],
            symbol_format="BASE-USDT",
            requires_api_key=False,
            requires_authentication=False,
            requires_proxy=False,  # CoinGecko 全球可直连
            has_rate_limit=True,
            rate_limit_per_minute=50,
            supports_real_time=False,
            supports_websocket=False,
        )
    
    @property
    def _service(self):
        """延迟加载旧服务并注入代理"""
        if self._legacy_service is None:
            self._legacy_service = legacy_services.CoinGeckoMarketService()
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
        """CoinGecko 不支持 K线数据"""
        raise PluginError("CoinGecko 不支持 K线数据，仅支持行情数据")
    
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
            logger.error(f"CoinGecko 获取行情数据失败: {e}")
            raise PluginError(f"CoinGecko 获取行情数据失败: {e}")
