# -*- coding: utf-8 -*-
"""
OKX 交易所数据源插件
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


class OKXMarketPlugin(MarketDataSourcePlugin):
    """OKX 交易所数据源插件"""
    
    def __init__(self):
        self._legacy_service = None
        super().__init__()
    
    def _get_metadata(self) -> DataSourceMetadata:
        """获取 OKX 元数据"""
        return DataSourceMetadata(
            name="okx",
            display_name="OKX 交易所",
            description="全球领先的数字资产交易平台，支持现货、期货、永续合约等多种交易产品",
            source_type=SourceType.EXCHANGE,
            website="https://www.okx.com",
            api_base_url="https://www.okx.com/api/v5",
            plugin_version="1.0.0",
            author="GeneticGrid Team",
            last_updated=datetime(2025, 1, 5),
            is_active=True,
            is_experimental=False,
            requires_proxy=True,  # OKX 在中国需要代理
        )
    
    def _get_capability(self) -> Capability:
        """获取 OKX 能力"""
        return Capability(
            supports_candlesticks=True,
            candlestick_granularities=[
                "1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w", "1M"
            ],
            candlestick_limit=300,
            candlestick_max_history_days=None,  # 无限制
            supports_ticker=True,
            ticker_update_frequency=1,
            supported_symbols=[],  # 动态获取
            symbol_format="BASE-USDT",
            requires_api_key=False,
            requires_authentication=False,
            requires_proxy=True,  # OKX 在中国需要代理
            has_rate_limit=True,
            rate_limit_per_minute=600,
            supports_real_time=False,
            supports_websocket=True,
        )
    
    @property
    def _service(self):
        """延迟加载旧服务并注入代理"""
        if self._legacy_service is None:
            self._legacy_service = legacy_services.OKXMarketService()
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
            # 使用旧服务获取数据
            response = self._service.get_candlesticks(
                inst_id=symbol,
                bar=bar,
                limit=min(limit, 300),
            )
            
            # 转换为标准格式
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
            logger.error(f"OKX 获取 K线数据失败: {e}")
            raise PluginError(f"OKX 获取 K线数据失败: {e}")
    
    def get_ticker(self, symbol: str) -> TickerData:
        """获取行情数据"""
        try:
            response = self._service.get_ticker(inst_id=symbol)
            
            # OKX 返回字段: askPx, bidPx, open24h, high24h, low24h
            last = float(response['last'])
            open_24h = float(response.get('open24h', 0))
            
            # 计算24h涨跌
            change_24h = last - open_24h if open_24h else None
            change_24h_pct = (change_24h / open_24h * 100) if open_24h and change_24h else None
            
            return TickerData(
                inst_id=symbol,
                last=last,
                bid=float(response.get('bidPx', 0)) or None,
                ask=float(response.get('askPx', 0)) or None,
                high_24h=float(response.get('high24h', 0)) or None,
                low_24h=float(response.get('low24h', 0)) or None,
                change_24h=change_24h,
                change_24h_pct=change_24h_pct,
            )
        except Exception as e:
            logger.error(f"OKX 获取行情数据失败: {e}")
            raise PluginError(f"OKX 获取行情数据失败: {e}")
