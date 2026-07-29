# -*- coding: utf-8 -*-
"""
CoinGecko 数据聚合器插件
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
    SymbolMode,
)

logger = logging.getLogger(__name__)


class CoinGeckoMarketPlugin(MarketDataSourcePlugin):
    """CoinGecko 数据聚合器插件
    
    协议实现：
    - 接收标准格式：symbol="BTCUSDT"
    - 内部转换为：coin_id="bitcoin"
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    # 币种 ID 映射
    COIN_ID_MAP = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "XRP": "ripple",
        "DOGE": "dogecoin",
        "ADA": "cardano",
        "AVAX": "avalanche-2",
        "LINK": "chainlink",
        "DOT": "polkadot",
        "MATIC": "matic-network",
        "BNB": "binancecoin",
    }
    
    def __init__(self):
        self._session = None
        self._tickers_cache: Optional[dict] = None  # {"data": [...], "ts": 0}
        super().__init__()
    
    def _normalize_symbol(
        self,
        symbol: str,
        mode: str = SymbolMode.SPOT.value,
    ) -> str:
        """标准格式 "BTCUSDT" -> CoinGecko 格式 "bitcoin" """
        symbol = symbol.upper().replace('-', '').replace('/', '')
        
        # 提取基础币种
        for quote in ['USDT', 'USDC', 'USD', 'BTC', 'ETH']:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                coin_id = self.COIN_ID_MAP.get(base)
                if coin_id:
                    return coin_id
                raise PluginError(f"不支持的币种: {base}")
        
        # 默认：假设后4位是计价币种
        if len(symbol) > 4:
            base = symbol[:-4]
            coin_id = self.COIN_ID_MAP.get(base)
            if coin_id:
                return coin_id
        
        raise PluginError(f"不支持的币种: {symbol}")
    
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
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
                "ADAUSDT", "AVAXUSDT", "LINKUSDT", "BNBUSDT"
            ],
            symbol_format="BTCUSDT",  # 标准格式
            symbol_modes=[SymbolMode.SPOT.value],
            requires_api_key=False,
            requires_authentication=False,
            requires_proxy=False,  # CoinGecko 全球可直连
            has_rate_limit=True,
            rate_limit_per_minute=50,
            supports_real_time=False,
            supports_websocket=False,
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
    
    def _get_candlesticks_impl(
        self,
        coin_id: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
        mode: str = SymbolMode.SPOT.value,
    ) -> List[CandleData]:
        """CoinGecko 不支持 K线数据"""
        raise PluginError("CoinGecko 不支持 K线数据，仅支持行情数据")
    
    def _get_ticker_impl(
        self,
        coin_id: str,
        mode: str = SymbolMode.SPOT.value,
    ) -> TickerData:
        """获取行情数据的内部实现（coin_id 已转换为 bitcoin 等）"""
        try:
            if mode != SymbolMode.SPOT.value:
                raise PluginError("CoinGecko 仅提供现货行情数据")
            # coin_id 已经通过 _normalize_symbol 转换了，直接使用
            # CoinGecko API - Simple Price
            url = f"{self.BASE_URL}/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
            }
            
            response = self._get_session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if coin_id not in data:
                raise PluginError(f"CoinGecko 未返回 {coin_id} 数据")
            
            coin_data = data[coin_id]
            last_price = float(coin_data.get('usd', 0))
            change_24h_pct = float(coin_data.get('usd_24h_change', 0)) or None
            
            # 计算24h变化金额
            change_24h = None
            if change_24h_pct and last_price:
                change_24h = last_price * (change_24h_pct / 100)
            
            return TickerData(
                inst_id=coin_id,
                last=last_price,
                bid=None,  # CoinGecko 不提供买卖价
                ask=None,
                high_24h=None,  # 简单接口不提供高低价
                low_24h=None,
                change_24h=change_24h,
                change_24h_pct=change_24h_pct,
            )
            
        except requests.exceptions.Timeout:
            logger.error("CoinGecko API 连接超时")
            raise PluginError("CoinGecko API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"CoinGecko 获取行情数据失败: {e}")
            raise PluginError(f"CoinGecko 获取行情数据失败: {e}")
        except Exception as e:
            logger.error(f"CoinGecko 获取行情数据失败: {e}")
            raise PluginError(f"CoinGecko 获取行情数据失败: {e}")
    
    def get_tickers(self, mode: str = 'spot', limit: int = 100) -> List[dict]:
        """按市值降序获取批量行情数据（用于前端符号选择器排序）
        
        调用 CoinGecko /coins/markets 接口，返回按市值排序的代币列表。
        结果缓存 5 分钟以避免触发免费 API 速率限制。
        """
        # 缓存检查：5 分钟内有效
        CACHE_TTL = 300  # 5 分钟
        now = __import__('time').time()
        if self._tickers_cache and (now - self._tickers_cache['ts']) < CACHE_TTL:
            logger.debug("CoinGecko tickers 缓存命中")
            return self._tickers_cache['data']
        
        try:
            url = f"{self.BASE_URL}/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": str(min(limit, 250)),
                "page": "1",
                "sparkline": "false",
                "price_change_percentage": "24h",
            }
            response = self._get_session.get(url, params=params, timeout=15)
            response.raise_for_status()
            coins = response.json()

            # 构建 coin_id → base_symbol 反向映射
            id_to_base = {v: k for k, v in self.COIN_ID_MAP.items()}

            results = []
            for coin in coins:
                coin_id = coin.get("id", "")
                base_symbol = id_to_base.get(coin_id, "")
                if not base_symbol:
                    continue
                symbol = f"{base_symbol}USDT"
                last_price = coin.get("current_price") or 0
                market_cap = coin.get("market_cap")
                market_cap_rank = coin.get("market_cap_rank")
                change_24h_pct = coin.get("price_change_percentage_24h")
                volume_24h = coin.get("total_volume")

                results.append({
                    "inst_id": symbol,
                    "last": float(last_price),
                    "market_cap": float(market_cap) if market_cap else None,
                    "market_cap_rank": int(market_cap_rank) if market_cap_rank else None,
                    "change_24h_pct": float(change_24h_pct) if change_24h_pct else None,
                    "volume_24h": float(volume_24h) if volume_24h else None,
                })

            # 补充未在 top 中的已知币种（如 BNB 可能在 page 2）
            seen_ids = {coin.get("id") for coin in coins}
            for base, coin_id in self.COIN_ID_MAP.items():
                if coin_id in seen_ids:
                    continue
                symbol = f"{base}USDT"
                try:
                    detail_url = f"{self.BASE_URL}/coins/{coin_id}"
                    detail_resp = self._get_session.get(detail_url, params={
                        "localization": "false", "tickers": "false",
                        "market_data": "true", "community_data": "false", "developer_data": "false",
                    }, timeout=10)
                    detail_resp.raise_for_status()
                    detail = detail_resp.json()
                    md = detail.get("market_data", {})
                    results.append({
                        "inst_id": symbol,
                        "last": float(md.get("current_price", {}).get("usd", 0)),
                        "market_cap": float(md["market_cap"]["usd"]) if md.get("market_cap", {}).get("usd") else None,
                        "market_cap_rank": detail.get("market_cap_rank"),
                        "change_24h_pct": md.get("price_change_percentage_24h"),
                        "volume_24h": float(md["total_volume"]["usd"]) if md.get("total_volume", {}).get("usd") else None,
                    })
                except Exception as e:
                    logger.warning(f"获取 {coin_id} 详情失败: {e}")

            # 按市值降序排列
            results.sort(key=lambda x: x["market_cap"] if x["market_cap"] else 0, reverse=True)
            
            # 写入缓存
            self._tickers_cache = {'data': results, 'ts': now}
            return results

        except requests.exceptions.Timeout:
            logger.error("CoinGecko tickers API 连接超时")
            raise PluginError("CoinGecko tickers API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"CoinGecko 获取 tickers 失败: {e}")
            raise PluginError(f"CoinGecko 获取 tickers 失败: {e}")
