# 行情服务 - 支持多数据源
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .proxy_config import configure_requests_proxies, get_okx_proxy
import logging

logger = logging.getLogger(__name__)

# 全局 Session 复用连接池
_session = None

def get_session():
    """获取复用的 requests session，带连接池、重试和代理支持"""
    global _session
    if _session is None:
        _session = requests.Session()
        # 配置重试策略
        retry = Retry(total=2, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=retry)
        _session.mount('https://', adapter)
        _session.mount('http://', adapter)
        
        # 配置代理
        configure_requests_proxies(_session)
    return _session


class MarketAPIError(Exception):
    """行情 API 调用异常"""
    pass


class BinanceMarketService:
    """Binance 公开行情接口（无需 API Key，全球可访问）"""
    
    BASE_URL = "https://api.binance.com"
    
    def __init__(self, timeout=5):
        self.timeout = timeout
        self.session = get_session()
    
    def _convert_symbol(self, inst_id: str) -> str:
        """将 OKX 格式转换为 Binance 格式: BTC-USDT -> BTCUSDT"""
        return inst_id.replace("-", "")
    
    def _convert_bar(self, bar: str) -> str:
        """将时间周期转换为 Binance 格式"""
        mapping = {
            "1s": "1s", "5s": "1s", "15s": "1s", "30s": "1s",  # Binance只支持1s，其他秒级用1s代替
            "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "1H": "1h", "2h": "2h", "4h": "4h", "4H": "4h",
            "6h": "6h", "12h": "12h",
            "1d": "1d", "1D": "1d", "3d": "3d", 
            "1w": "1w", "1W": "1w", "1M": "1M"
        }
        return mapping.get(bar, "1h")
    
    def get_candlesticks(self, inst_id: str = "BTC-USDT", bar: str = "1H", limit: int = 100, before: int = None):
        """获取 K 线数据
        :param before: 获取该时间戳之前的数据（毫秒）
        """
        symbol = self._convert_symbol(inst_id)
        interval = self._convert_bar(bar)
        
        url = f"{self.BASE_URL}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000)
        }
        
        if before:
            params["endTime"] = before - 1
        
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            raise MarketAPIError("Binance API 连接超时")
        except requests.exceptions.RequestException as e:
            raise MarketAPIError(f"Binance API 网络错误: {str(e)}")
        
        if isinstance(data, dict) and data.get("code"):
            raise MarketAPIError(f"Binance API 错误: {data.get('msg', '未知错误')}")
        
        # Binance 返回格式: [[openTime, open, high, low, close, volume, ...], ...]
        candles = []
        for item in data:
            candles.append({
                "time": int(item[0]) // 1000,
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
            })
        return candles
    
    def get_ticker(self, inst_id: str = "BTC-USDT"):
        """获取最新行情"""
        symbol = self._convert_symbol(inst_id)
        
        # 使用更轻量的 ticker/price 接口获取最新价，再用 ticker/24hr 获取其他数据
        url = f"{self.BASE_URL}/api/v3/ticker/24hr"
        params = {"symbol": symbol}
        
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            raise MarketAPIError("Binance API 连接超时")
        except requests.exceptions.RequestException as e:
            raise MarketAPIError(f"Binance API 网络错误: {str(e)}")
        
        if data.get("code"):
            raise MarketAPIError(f"Binance API 错误: {data.get('msg', '未知错误')}")
        
        return {
            "instId": inst_id,
            "last": data.get("lastPrice"),
            "open24h": data.get("openPrice"),
            "high24h": data.get("highPrice"),
            "low24h": data.get("lowPrice"),
            "vol24h": data.get("volume"),
            "volCcy24h": data.get("quoteVolume"),
        }


class TradingViewMarketService(BinanceMarketService):
    """TradingView 数据服务 (目前使用 Binance 数据作为代理)"""
    pass


class CoinGeckoMarketService:
    """CoinGecko 公开行情接口（无需 API Key）"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    # 交易对到 CoinGecko ID 的映射
    COIN_IDS = {
        "BTC-USDT": "bitcoin",
        "ETH-USDT": "ethereum",
        "SOL-USDT": "solana",
        "XRP-USDT": "ripple",
        "DOGE-USDT": "dogecoin",
        "ADA-USDT": "cardano",
        "AVAX-USDT": "avalanche-2",
        "LINK-USDT": "chainlink",
    }
    
    def __init__(self, timeout=5):
        self.timeout = timeout
        self.session = get_session()
    
    def _get_coin_id(self, inst_id: str) -> str:
        coin_id = self.COIN_IDS.get(inst_id)
        if not coin_id:
            raise MarketAPIError(f"CoinGecko 不支持该交易对: {inst_id}")
        return coin_id
    
    def _bar_to_days(self, bar: str) -> int:
        """将时间周期转换为天数"""
        mapping = {
            "1m": 1, "5m": 1, "15m": 1, "30m": 1,
            "1H": 2, "4H": 7, "1D": 90, "1W": 365
        }
        return mapping.get(bar, 2)
    
    def get_candlesticks(self, inst_id: str = "BTC-USDT", bar: str = "1H", limit: int = 100, before: int = None):
        """获取 K 线数据（OHLC）
        注意: CoinGecko 免费 API 不支持历史分页，before 参数会被忽略
        """
        coin_id = self._get_coin_id(inst_id)
        days = self._bar_to_days(bar)
        
        url = f"{self.BASE_URL}/coins/{coin_id}/ohlc"
        params = {
            "vs_currency": "usd",
            "days": days
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            raise MarketAPIError("CoinGecko API 连接超时")
        except requests.exceptions.RequestException as e:
            raise MarketAPIError(f"CoinGecko API 网络错误: {str(e)}")
        
        if isinstance(data, dict) and data.get("error"):
            raise MarketAPIError(f"CoinGecko API 错误: {data.get('error')}")
        
        # CoinGecko 返回格式: [[timestamp, open, high, low, close], ...]
        candles = []
        for item in data[-limit:]:
            candles.append({
                "time": int(item[0]) // 1000,
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": 0,  # CoinGecko OHLC 不包含成交量
            })
        return candles
    
    def get_ticker(self, inst_id: str = "BTC-USDT"):
        """获取最新行情"""
        coin_id = self._get_coin_id(inst_id)
        
        url = f"{self.BASE_URL}/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
            "include_last_updated_at": "true"
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            raise MarketAPIError("CoinGecko API 连接超时")
        except requests.exceptions.RequestException as e:
            raise MarketAPIError(f"CoinGecko API 网络错误: {str(e)}")
        
        coin_data = data.get(coin_id, {})
        if not coin_data:
            raise MarketAPIError(f"CoinGecko 未返回数据: {inst_id}")
        
        last_price = coin_data.get("usd", 0)
        change_24h = coin_data.get("usd_24h_change", 0)
        open_24h = last_price / (1 + change_24h / 100) if change_24h else last_price
        
        return {
            "instId": inst_id,
            "last": str(last_price),
            "open24h": str(open_24h),
            "high24h": str(last_price * 1.01),  # 估算值
            "low24h": str(last_price * 0.99),   # 估算值
            "vol24h": str(coin_data.get("usd_24h_vol", 0)),
            "volCcy24h": str(coin_data.get("usd_24h_vol", 0)),
        }


class OKXMarketService:
    """OKX 公开行情接口（无需 API Key）"""

    def __init__(self, proxy=None):
        import okx.MarketData as MarketData
        
        # 如果没有提供代理，使用配置模块的代理
        if proxy is None:
            proxy = get_okx_proxy()
        
        self.proxy = proxy
        logger.info(f"OKX Market Service 初始化，代理: {proxy or '无'}")
        
        try:
            if proxy:
                self.market_api = MarketData.MarketAPI(
                    flag="0",
                    proxy=proxy,
                )
            else:
                self.market_api = MarketData.MarketAPI(flag="0")
        except Exception as e:
            logger.warning(f"OKX MarketAPI 初始化失败，尝试不使用代理: {e}")
            self.market_api = MarketData.MarketAPI(flag="0")

    def get_candlesticks(self, inst_id: str = "BTC-USDT", bar: str = "1H", limit: int = 100, before: int = None):
        """获取 K 线数据
        :param before: 获取该时间戳之前的数据（毫秒）
        """
        try:
            params = {"instId": inst_id, "bar": bar, "limit": str(limit)}
            if before:
                params["before"] = str(before)
            result = self.market_api.get_candlesticks(**params)
        except Exception as e:
            raise MarketAPIError(f"OKX 网络连接失败: {str(e)}")
        
        if result.get("code") != "0":
            raise MarketAPIError(f"OKX API 错误: {result.get('msg', '未知错误')}")
        
        data = result.get("data", [])
        if not data:
            raise MarketAPIError("OKX 返回数据为空")
        
        candles = []
        for item in reversed(data):
            candles.append({
                "time": int(item[0]) // 1000,
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
            })
        return candles

    def get_ticker(self, inst_id: str = "BTC-USDT"):
        """获取最新行情"""
        try:
            result = self.market_api.get_ticker(instId=inst_id)
        except Exception as e:
            raise MarketAPIError(f"OKX 网络连接失败: {str(e)}")
        
        if result.get("code") != "0":
            raise MarketAPIError(f"OKX API 错误: {result.get('msg', '未知错误')}")
        
        data = result.get("data", [])
        if not data:
            raise MarketAPIError("OKX 返回数据为空")
        
        return data[0]


# 数据源工厂
MARKET_SERVICES = {
    "tradingview": TradingViewMarketService,
    "binance": BinanceMarketService,
    "coingecko": CoinGeckoMarketService,
    "okx": OKXMarketService,
}


def get_market_service(source: str = "tradingview"):
    """获取指定数据源的行情服务"""
    service_class = MARKET_SERVICES.get(source.lower())
    if not service_class:
        raise MarketAPIError(f"不支持的数据源: {source}")
    return service_class()
