# -*- coding: utf-8 -*-
"""
币安交易所数据源插件
"""

from typing import List, Optional, Dict
from datetime import datetime
import logging
import requests

from ..base import (
    MarketDataSourcePlugin,
    DataSourceMetadata,
    Capability,
    CandleData,
    TickerData,
    FundingRateData,
    ContractBasisData,
    SourceType,
    PluginError,
    SymbolMode,
)
from core.proxy_config import get_proxy
from .binance_stream import get_realtime_manager

logger = logging.getLogger(__name__)


class BinanceMarketPlugin(MarketDataSourcePlugin):
    """币安交易所数据源插件"""
    
    BASE_URL = "https://api.binance.com"
    FAPI_BASE_URL = "https://fapi.binance.com"  # 合约API
    
    def __init__(self):
        self._session = None
        self._realtime = get_realtime_manager()
        super().__init__()
    
    def _get_metadata(self) -> DataSourceMetadata:
        """获取币安元数据"""
        return DataSourceMetadata(
            name="binance",
            display_name="币安交易所",
            description="全球最大的加密货币交易平台，提供现货、合约、期权等多种交易产品，日交易量超过 300 亿美元",
            source_type=SourceType.EXCHANGE,
            website="https://www.binance.com",
            api_base_url="https://api.binance.com",
            plugin_version="2.0.0",
            author="GeneticGrid Team",
            last_updated=datetime(2025, 12, 5),
            is_active=True,
            is_experimental=False,
            requires_proxy=True,  # 币安在某些地区被墙
        )
    
    def _get_capability(self) -> Capability:
        """获取币安能力"""
        return Capability(
            supports_candlesticks=True,
            candlestick_granularities=[
                "1s",
                "1m", "3m", "5m", "15m", "30m",
                "1h", "2h", "4h", "6h", "12h",
                "1d", "3d", "1w", "1M"
            ],
            candlestick_limit=1000,  # Binance 最多返回 1000 条
            candlestick_max_history_days=None,
            supports_ticker=True,
            ticker_update_frequency=1,
            supported_symbols=[
                # 主流 USDT 交易对
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
                "SOLUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
                "AVAXUSDT", "LINKUSDT", "ATOMUSDT", "UNIUSDT", "ETCUSDT",
                "SHIBUSDT", "TRXUSDT", "BCHUSDT", "NEARUSDT", "APTUSDT",
                # Binance 支持 1000+ 交易对
            ],
            symbol_format="BTCUSDT",  # 币安格式
            symbol_modes=[SymbolMode.SPOT.value, SymbolMode.CONTRACT.value],
            requires_api_key=False,
            requires_authentication=False,
            requires_proxy=True,
            has_rate_limit=True,
            rate_limit_per_minute=1200,
            supports_real_time=False,
            supports_websocket=True,
            # 衍生品指标
            supports_funding_rate=True,
            funding_rate_interval_hours=8,
            funding_rate_quote_currency="USDT",
            supports_contract_basis=True,
            contract_basis_types=["perpetual"],
            contract_basis_tenors=["perpetual"],
        )
    
    @property
    def _get_session(self):
        """获取 requests session，自动配置代理"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': 'GeneticGrid/2.0'
            })
            # 配置代理
            self._session.proxies = self._get_proxies()
        return self._session
    
    def _get_proxies(self) -> Dict[str, str]:
        """获取代理配置"""
        proxy = get_proxy()
        if proxy:
            logger.info(f"Binance 使用代理: {proxy}")
            return {"http": proxy, "https": proxy}
        logger.warning("Binance 未配置代理，可能无法访问")
        return {}
    
    def _convert_symbol(self, inst_id: str, mode: str = SymbolMode.SPOT.value) -> str:
        """将标准格式转换为 Binance 格式: BTC-USDT -> BTCUSDT"""
        symbol = inst_id.replace("-", "")
        # 币安合约也使用相同格式
        return symbol
    
    def _convert_bar(self, bar: str) -> str:
        """将时间周期转换为 Binance 格式"""
        mapping = {
            "tick": "1s",
            "1s": "1s",
            "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "12h": "12h",
            "1d": "1d", "3d": "3d", "1w": "1w", "1M": "1M"
        }
        return mapping.get(bar, "1h")

    def _fetch_rest_candles(
        self,
        binance_symbol: str,
        interval: str,
        limit: int,
        before: Optional[int],
        mode: str = SymbolMode.SPOT.value
    ) -> List[CandleData]:
        """通过 REST API 获取 K 线数据"""
        # 根据模式选择不同的API端点
        if mode == SymbolMode.CONTRACT.value:
            url = f"{self.FAPI_BASE_URL}/fapi/v1/klines"
        else:
            url = f"{self.BASE_URL}/api/v3/klines"
            
        params = {
            "symbol": binance_symbol,
            "interval": interval,
            "limit": min(limit, 1000)
        }
        if before:
            params["endTime"] = before * 1000

        response = self._get_session.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not data:
            raise PluginError("Binance 返回数据为空")

        candles = []
        for item in data:
            candles.append(CandleData(
                time=int(item[0]) // 1000,
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
            ))
        return candles

    def _merge_realtime_data(
        self,
        rest_candles: List[CandleData],
        realtime_candles: List[CandleData],
        limit: int
    ) -> List[CandleData]:
        if not realtime_candles:
            return rest_candles

        merged = {c.time: c for c in rest_candles}
        for candle in realtime_candles:
            merged[candle.time] = candle
        ordered = sorted(merged.values(), key=lambda c: c.time)
        return ordered[-limit:]
    
    def _get_candlesticks_impl(
        self,
        symbol: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
        mode: str = SymbolMode.SPOT.value,
    ) -> List[CandleData]:
        """获取 K线数据"""
        try:
            binance_symbol = self._convert_symbol(symbol, mode)
            interval = self._convert_bar(bar)
            
            # 合约模式暂不支持实时WebSocket
            use_realtime = (
                mode == SymbolMode.SPOT.value and 
                interval == "1s" and 
                before is None and 
                self._realtime.enabled
            )

            realtime_candles: List[CandleData] = []
            if use_realtime:
                realtime_candles = self._realtime.get_latest_candles(
                    binance_symbol,
                    interval,
                    limit * 2
                )
                if len(realtime_candles) >= limit:
                    logger.debug("⚡ 使用 Binance WebSocket 实时缓存 (%s) 返回 %d 条数据", symbol, len(realtime_candles))
                    return realtime_candles[-limit:]

            rest_candles = self._fetch_rest_candles(binance_symbol, interval, limit, before, mode)

            if use_realtime and realtime_candles:
                merged = self._merge_realtime_data(rest_candles, realtime_candles, limit)
                logger.debug("🔄 合并实时与 REST 数据: REST=%d, WS=%d", len(rest_candles), len(realtime_candles))
                return merged

            return rest_candles
            
        except requests.exceptions.Timeout:
            logger.error("Binance API 连接超时")
            raise PluginError("Binance API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance 获取 K线数据失败: {e}")
            raise PluginError(f"Binance API 网络错误: {e}")
        except Exception as e:
            logger.error(f"Binance 获取 K线数据失败: {e}")
            raise PluginError(f"Binance 获取 K线数据失败: {e}")
    
    def _get_ticker_impl(
        self,
        symbol: str,
        mode: str = SymbolMode.SPOT.value,
    ) -> TickerData:
        """获取行情数据"""
        try:
            binance_symbol = self._convert_symbol(symbol, mode)
            
            # 根据模式选择不同的API端点
            if mode == SymbolMode.CONTRACT.value:
                url = f"{self.FAPI_BASE_URL}/fapi/v1/ticker/24hr"
            else:
                url = f"{self.BASE_URL}/api/v3/ticker/24hr"
                
            params = {"symbol": binance_symbol}
            
            response = self._get_session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            last = float(data['lastPrice'])
            open_price = float(data['openPrice'])
            
            # 计算24h涨跌
            change_24h = last - open_price
            change_24h_pct = (change_24h / open_price * 100) if open_price else None
            volume_24h = float(data.get('volume', 0) or 0)
            volume_24h = volume_24h if volume_24h > 0 else None
            
            return TickerData(
                inst_id=symbol,
                last=last,
                bid=float(data.get('bidPrice', 0)) or None,
                ask=float(data.get('askPrice', 0)) or None,
                high_24h=float(data.get('highPrice', 0)) or None,
                low_24h=float(data.get('lowPrice', 0)) or None,
                change_24h=change_24h,
                change_24h_pct=change_24h_pct,
                volume_24h=volume_24h,
            )
            
        except requests.exceptions.Timeout:
            logger.error("Binance API 连接超时")
            raise PluginError("Binance API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance 获取行情数据失败: {e}")
            raise PluginError(f"Binance API 网络错误: {e}")
        except Exception as e:
            logger.error(f"Binance 获取行情数据失败: {e}")
            raise PluginError(f"Binance 获取行情数据失败: {e}")
    
    def _get_funding_rate_impl(self, symbol: str) -> FundingRateData:
        """获取资金费率 - 仅合约"""
        try:
            binance_symbol = self._convert_symbol(symbol, SymbolMode.CONTRACT.value)
            
            # 币安合约API获取资金费率
            url = f"{self.FAPI_BASE_URL}/fapi/v1/premiumIndex"
            params = {"symbol": binance_symbol}
            
            response = self._get_session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # 解析资金费率数据
            funding_rate = float(data.get('lastFundingRate', 0))
            next_funding_time = int(data.get('nextFundingTime', 0)) // 1000 if data.get('nextFundingTime') else None
            timestamp = int(data.get('time', 0)) // 1000 if data.get('time') else None
            
            # 获取标记价格和指数价格
            mark_price = float(data.get('markPrice', 0)) if data.get('markPrice') else None
            index_price = float(data.get('indexPrice', 0)) if data.get('indexPrice') else None
            
            return FundingRateData(
                inst_id=symbol,
                funding_rate=funding_rate,
                timestamp=timestamp,
                funding_interval_hours=8,  # 币安每8小时结算一次
                next_funding_time=next_funding_time,
                predicted_funding_rate=None,  # 币安不提供预测费率
                index_price=index_price,
                premium_index=mark_price - index_price if mark_price and index_price else None,
                quote_currency="USDT"
            )
            
        except requests.exceptions.Timeout:
            logger.error("Binance 资金费率API 连接超时")
            raise PluginError("Binance 资金费率API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance 获取资金费率失败: {e}")
            raise PluginError(f"Binance 资金费率API 网络错误: {e}")
        except Exception as e:
            logger.error(f"Binance 获取资金费率失败: {e}")
            raise PluginError(f"Binance 获取资金费率失败: {e}")
    
    def get_funding_rate_history(self, symbol: str, limit: int = 100) -> List[dict]:
        """获取资金费率历史数据"""
        try:
            binance_symbol = self._convert_symbol(symbol, SymbolMode.CONTRACT.value)
            
            url = f"{self.FAPI_BASE_URL}/fapi/v1/fundingRate"
            params = {
                "symbol": binance_symbol,
                "limit": min(limit, 1000)  # 币安限制最多1000条
            }
            
            response = self._get_session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            history = []
            for item in data:
                funding_time = int(item.get('fundingTime', 0)) // 1000 if item.get('fundingTime') else None
                funding_rate = float(item.get('fundingRate', 0))
                
                history.append({
                    "timestamp": funding_time,
                    "funding_rate": funding_rate,
                    "inst_id": binance_symbol
                })
            
            # 按时间排序（从旧到新）
            history.sort(key=lambda x: x["timestamp"] if x["timestamp"] else 0)
            return history
            
        except requests.exceptions.Timeout:
            logger.error("Binance 资金费率历史API 连接超时")
            raise PluginError("Binance 资金费率历史API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance 获取资金费率历史失败: {e}")
            raise PluginError(f"Binance 资金费率历史API 网络错误: {e}")
        except Exception as e:
            logger.error(f"Binance 获取资金费率历史失败: {e}")
            raise PluginError(f"Binance 获取资金费率历史失败: {e}")
    
    def _get_contract_basis_impl(
        self,
        symbol: str,
        contract_type: str,
        reference_symbol: Optional[str] = None,
        tenor: Optional[str] = None,
    ) -> ContractBasisData:
        """获取合约基差"""
        try:
            binance_symbol = self._convert_symbol(symbol, SymbolMode.CONTRACT.value)
            
            # 获取合约价格（标记价格）
            fapi_url = f"{self.FAPI_BASE_URL}/fapi/v1/ticker/price"
            fapi_params = {"symbol": binance_symbol}
            
            fapi_response = self._get_session.get(fapi_url, params=fapi_params, timeout=15)
            fapi_response.raise_for_status()
            fapi_data = fapi_response.json()
            contract_price = float(fapi_data.get('price', 0))
            
            # 获取现货价格作为参考
            spot_url = f"{self.BASE_URL}/api/v3/ticker/price"
            spot_params = {"symbol": binance_symbol}
            
            spot_response = self._get_session.get(spot_url, params=spot_params, timeout=15)
            spot_response.raise_for_status()
            spot_data = spot_response.json()
            reference_price = float(spot_data.get('price', 0))
            
            # 计算基差
            basis = contract_price - reference_price
            basis_rate = (basis / reference_price * 100) if reference_price != 0 else 0.0
            
            import time
            timestamp = int(time.time())
            
            # 从交易对中提取基础货币
            # BTCUSDT -> BTC
            base_currency = binance_symbol.replace('USDT', '').replace('BUSD', '')
            
            return ContractBasisData(
                inst_id=symbol,
                contract_type=contract_type or "perpetual",
                basis=basis,
                timestamp=timestamp,
                basis_rate=basis_rate,
                contract_price=contract_price,
                reference_symbol=base_currency,
                reference_price=reference_price,
                tenor="perpetual",
                quote_currency="USDT"
            )
            
        except requests.exceptions.Timeout:
            logger.error("Binance 合约基差API 连接超时")
            raise PluginError("Binance 合约基差API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance 获取合约基差失败: {e}")
            raise PluginError(f"Binance 合约基差API 网络错误: {e}")
        except Exception as e:
            logger.error(f"Binance 获取合约基差失败: {e}")
            raise PluginError(f"Binance 获取合约基差失败: {e}")
    
    def get_contract_basis_history(
        self,
        symbol: str,
        contract_type: str = "perpetual",
        limit: int = 100,
        granularity: str = "1h"
    ) -> List[dict]:
        """获取合约基差历史数据
        
        币安不直接提供基差历史，需要通过K线数据计算
        """
        try:
            binance_symbol = self._convert_symbol(symbol, SymbolMode.CONTRACT.value)
            
            # 转换granularity到币安格式
            interval = self._convert_bar(granularity)
            
            # 获取合约K线
            contract_url = f"{self.FAPI_BASE_URL}/fapi/v1/klines"
            contract_params = {
                "symbol": binance_symbol,
                "interval": interval,
                "limit": min(limit, 1000)
            }
            
            contract_response = self._get_session.get(contract_url, params=contract_params, timeout=15)
            contract_response.raise_for_status()
            contract_klines = contract_response.json()
            
            # 获取现货K线
            spot_url = f"{self.BASE_URL}/api/v3/klines"
            spot_params = {
                "symbol": binance_symbol,
                "interval": interval,
                "limit": min(limit, 1000)
            }
            
            spot_response = self._get_session.get(spot_url, params=spot_params, timeout=15)
            spot_response.raise_for_status()
            spot_klines = spot_response.json()
            
            # 计算基差历史
            history = []
            for contract_k, spot_k in zip(contract_klines, spot_klines):
                timestamp = int(contract_k[0]) // 1000
                contract_close = float(contract_k[4])
                spot_close = float(spot_k[4])
                
                basis = contract_close - spot_close
                basis_rate = (basis / spot_close * 100) if spot_close != 0 else 0.0
                
                history.append({
                    "timestamp": timestamp,
                    "basis": basis,
                    "basis_rate": basis_rate,
                    "contract_price": contract_close,
                    "spot_price": spot_close,
                    "inst_id": binance_symbol
                })
            
            return history
            
        except requests.exceptions.Timeout:
            logger.error("Binance 合约基差历史API 连接超时")
            raise PluginError("Binance 合约基差历史API 连接超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance 获取合约基差历史失败: {e}")
            raise PluginError(f"Binance 合约基差历史API 网络错误: {e}")
        except Exception as e:
            logger.error(f"Binance 获取合约基差历史失败: {e}")
            raise PluginError(f"Binance 获取合约基差历史失败: {e}")
