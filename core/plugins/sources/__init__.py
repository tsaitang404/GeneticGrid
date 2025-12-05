# -*- coding: utf-8 -*-
"""
数据源插件包
"""

from .okx_plugin import OKXMarketPlugin
from .binance_plugin import BinanceMarketPlugin
from .coinbase_plugin import CoinbaseMarketPlugin
from .coingecko_plugin import CoinGeckoMarketPlugin
from .kraken_plugin import KrakenMarketPlugin
from .bybit_plugin import BybitMarketPlugin

__all__ = [
    'OKXMarketPlugin',
    'BinanceMarketPlugin',
    'CoinbaseMarketPlugin',
    'CoinGeckoMarketPlugin',
    'KrakenMarketPlugin',
    'BybitMarketPlugin',
]
