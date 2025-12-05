# -*- coding: utf-8 -*-
"""
已废弃：请使用插件系统

旧的服务层已完全移除，所有数据源现在通过插件系统提供。

使用方法:
    from core.plugins.manager import PluginManager
    
    manager = PluginManager()
    plugin = manager.get_plugin('binance')
    ticker = plugin.get_ticker('BTC-USDT')
    
可用插件:
    - binance: 币安交易所
    - bybit: Bybit交易所
    - kraken: Kraken交易所
    - coinbase: Coinbase交易所
    - coingecko: CoinGecko聚合器
    - okx: OKX交易所
    - tradingview: TradingView
"""

import logging

logger = logging.getLogger(__name__)


class MarketAPIError(Exception):
    """行情 API 调用异常"""
    pass


def get_market_service(source: str = "binance"):
    """
    ⚠️ 已废弃: 请使用插件系统
    
    Args:
        source: 数据源名称
        
    Raises:
        DeprecationWarning: 此函数已废弃
    """
    logger.error(
        f"❌ get_market_service('{source}') 已废弃！\n"
        f"   请使用插件系统:\n"
        f"   from core.plugins.manager import PluginManager\n"
        f"   manager = PluginManager()\n"
        f"   plugin = manager.get_plugin('{source}')\n"
    )
    raise DeprecationWarning(
        "get_market_service() 已废弃，请使用插件系统。"
        "参考: core/plugins/manager.py"
    )


# 废弃的常量
MARKET_SERVICES = {}
