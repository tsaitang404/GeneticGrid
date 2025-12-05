# -*- coding: utf-8 -*-
"""
数据源插件实现
"""

from .okx_plugin import OKXMarketPlugin
from .binance_plugin import BinanceMarketPlugin
from .coinbase_plugin import CoinbaseMarketPlugin
from .coingecko_plugin import CoinGeckoMarketPlugin
from .tradingview_plugin import TradingViewMarketPlugin

__all__ = [
    'OKXMarketPlugin',
    'BinanceMarketPlugin',
    'CoinbaseMarketPlugin',
    'CoinGeckoMarketPlugin',
    'TradingViewMarketPlugin',
]
