# -*- coding: utf-8 -*-
"""
数据源插件基类和标准数据结构

定义所有数据源必须遵守的标准接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


class SourceType(Enum):
    """数据源类型"""
    EXCHANGE = "exchange"          # 交易所
    AGGREGATOR = "aggregator"      # 数据聚合器
    CHARTING = "charting"          # 制图工具


class Granularity:
    """时间粒度定义"""
    
    # 标准粒度
    GRANULARITIES = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "2h": 7200,
        "4h": 14400,
        "6h": 21600,
        "12h": 43200,
        "1d": 86400,
        "1w": 604800,
        "1M": 2592000,  # 30 天近似
    }
    
    # 粒度优先级（用于降级）
    PRIORITY = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w", "1M"]
    
    @classmethod
    def is_valid(cls, bar: str) -> bool:
        """检查是否是有效的粒度"""
        return bar in cls.GRANULARITIES
    
    @classmethod
    def to_seconds(cls, bar: str) -> Optional[int]:
        """将粒度转换为秒"""
        return cls.GRANULARITIES.get(bar)
    
    @classmethod
    def find_closest_supported(cls, requested: str, supported: List[str]) -> Optional[str]:
        """找到最接近的支持粒度"""
        if requested in supported:
            return requested
        
        if requested not in cls.GRANULARITIES:
            return None
        
        requested_idx = cls.PRIORITY.index(requested) if requested in cls.PRIORITY else -1
        if requested_idx == -1:
            return None
        
        # 向上查找支持的粒度
        for i in range(requested_idx, len(cls.PRIORITY)):
            if cls.PRIORITY[i] in supported:
                return cls.PRIORITY[i]
        
        # 向下查找支持的粒度
        for i in range(requested_idx, -1, -1):
            if cls.PRIORITY[i] in supported:
                return cls.PRIORITY[i]
        
        return None


@dataclass
class Capability:
    """数据源能力描述"""
    
    # K线数据相关
    supports_candlesticks: bool = False
    candlestick_granularities: List[str] = field(default_factory=list)  # 支持的粒度
    candlestick_limit: int = 100  # 单次请求最大条数
    candlestick_max_history_days: Optional[int] = None  # 历史数据最多回溯多少天
    
    # Ticker 数据相关
    supports_ticker: bool = False
    ticker_update_frequency: Optional[int] = None  # 更新频率（秒）
    
    # 交易对相关
    supported_symbols: List[str] = field(default_factory=list)
    symbol_format: str = "BASE-QUOTE"  # 如 "BTC-USDT" 或 "BTCUSDT"
    
    # 其他特性
    requires_api_key: bool = False
    requires_authentication: bool = False
    requires_proxy: bool = False  # 是否需要代理访问
    has_rate_limit: bool = False
    rate_limit_per_minute: Optional[int] = None
    
    # 额外特性
    supports_real_time: bool = False
    supports_websocket: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'supports_candlesticks': self.supports_candlesticks,
            'candlestick_granularities': self.candlestick_granularities,
            'candlestick_limit': self.candlestick_limit,
            'candlestick_max_history_days': self.candlestick_max_history_days,
            'supports_ticker': self.supports_ticker,
            'ticker_update_frequency': self.ticker_update_frequency,
            'supported_symbols': self.supported_symbols,
            'symbol_format': self.symbol_format,
            'requires_api_key': self.requires_api_key,
            'requires_authentication': self.requires_authentication,
            'requires_proxy': self.requires_proxy,
            'has_rate_limit': self.has_rate_limit,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'supports_real_time': self.supports_real_time,
            'supports_websocket': self.supports_websocket,
        }


@dataclass
class DataSourceMetadata:
    """数据源元数据"""
    
    name: str  # 唯一标识符，如 "okx", "binance", "coinbase"
    display_name: str  # 显示名称，如 "OKX 交易所"
    description: str  # 详细描述
    source_type: SourceType  # 数据源类型
    website: Optional[str] = None  # 官网
    api_base_url: Optional[str] = None  # API 基础 URL
    
    # 版本和兼容性
    plugin_version: str = "1.0.0"
    min_api_version: str = "1.0.0"
    
    # 维护信息
    author: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    # 可用性
    is_active: bool = True
    is_experimental: bool = False
    requires_proxy: bool = False  # 是否需要通过代理访问
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'source_type': self.source_type.value,
            'website': self.website,
            'api_base_url': self.api_base_url,
            'plugin_version': self.plugin_version,
            'is_active': self.is_active,
            'is_experimental': self.is_experimental,
        }


@dataclass
class CandleData:
    """K线数据"""
    time: int  # Unix 时间戳（秒）
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'time': self.time,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
        }


@dataclass
class TickerData:
    """行情数据"""
    inst_id: str  # 交易对
    last: float  # 最新价格
    bid: Optional[float] = None
    ask: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    change_24h: Optional[float] = None
    change_24h_pct: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'inst_id': self.inst_id,
            'last': self.last,
            'bid': self.bid,
            'ask': self.ask,
            'high_24h': self.high_24h,
            'low_24h': self.low_24h,
            'change_24h': self.change_24h,
            'change_24h_pct': self.change_24h_pct,
        }


class MarketDataSourcePlugin(ABC):
    """
    数据源插件基类
    
    所有数据源都必须继承此类并实现所有抽象方法。
    
    协议约定：
    - 交易对格式：统一使用无分隔符格式，如 "BTCUSDT"
    - 时间粒度：统一使用小写格式，如 "1m", "1h", "1d"
    - 时间戳：统一使用秒级 Unix 时间戳
    """
    
    def __init__(self):
        """初始化插件"""
        self._metadata = self._get_metadata()
        self._capability = self._get_capability()
    
    @abstractmethod
    def _get_metadata(self) -> DataSourceMetadata:
        """获取数据源元数据（由子类实现）"""
        pass
    
    @abstractmethod
    def _get_capability(self) -> Capability:
        """获取数据源能力（由子类实现）"""
        pass
    
    def _normalize_symbol(self, symbol: str) -> str:
        """标准化交易对格式（由子类覆盖实现内部转换）
        
        输入：标准格式 "BTCUSDT"
        输出：数据源特定格式，如 "BTC-USDT" (OKX), "BTCUSDT" (Binance)
        
        默认实现：直接返回，适用于无分隔符格式的数据源
        """
        return symbol
    
    def _normalize_granularity(self, bar: str) -> str:
        """标准化时间粒度格式（由子类覆盖实现内部转换）
        
        输入：标准格式 "1h", "1d"
        输出：数据源特定格式，如 "1H" (OKX), "60" (Bybit)
        
        默认实现：直接返回
        """
        return bar
    
    def _normalize_timestamp(self, timestamp: Optional[int]) -> Optional[int]:
        """标准化时间戳（由子类覆盖实现内部转换）
        
        输入：秒级 Unix 时间戳
        输出：数据源特定格式（秒或毫秒）
        
        默认实现：直接返回秒级时间戳
        """
        return timestamp
    
    def _denormalize_timestamp(self, timestamp: int) -> int:
        """反标准化时间戳（由子类覆盖实现）
        
        输入：数据源返回的时间戳
        输出：标准秒级 Unix 时间戳
        
        默认实现：直接返回
        """
        return timestamp
    
    @abstractmethod
    def _get_candlesticks_impl(
        self,
        symbol: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
    ) -> List[CandleData]:
        """获取 K线数据的内部实现（由子类实现，使用数据源格式）"""
        pass
    
    @abstractmethod
    def _get_ticker_impl(self, symbol: str) -> TickerData:
        """获取行情数据的内部实现（由子类实现，使用数据源格式）"""
        pass
    
    def get_candlesticks(
        self,
        symbol: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
    ) -> List[CandleData]:
        """
        获取 K线数据（统一接口）
        
        Args:
            symbol: 交易对（标准格式："BTCUSDT"）
            bar: 时间粒度（标准格式："1h", "1d"）
            limit: 返回条数
            before: 之前的 Unix 时间戳（秒）
        
        Returns:
            K线数据列表（时间戳已标准化为秒）
        
        Raises:
            PluginError: 如果数据源不支持或发生错误
        """
        # 转换为数据源格式
        source_symbol = self._normalize_symbol(symbol)
        source_bar = self._normalize_granularity(bar)
        source_before = self._normalize_timestamp(before)
        
        # 调用子类实现
        candles = self._get_candlesticks_impl(source_symbol, source_bar, limit, source_before)
        
        # 确保时间戳标准化
        for candle in candles:
            candle.time = self._denormalize_timestamp(candle.time)
        
        return candles
    
    def get_ticker(self, symbol: str) -> TickerData:
        """
        获取最新行情数据（统一接口）
        
        Args:
            symbol: 交易对（标准格式："BTCUSDT"）
        
        Returns:
            行情数据
        
        Raises:
            PluginError: 如果数据源不支持或发生错误
        """
        # 转换为数据源格式
        source_symbol = self._normalize_symbol(symbol)
        
        # 调用子类实现
        ticker = self._get_ticker_impl(source_symbol)
        
        # 标准化交易对名称
        ticker.inst_id = symbol
        
        return ticker
    
    def get_supported_symbols(self) -> List[str]:
        """获取支持的交易对列表"""
        return self._capability.supported_symbols
    
    def get_metadata(self) -> DataSourceMetadata:
        """获取元数据"""
        return self._metadata
    
    def get_capability(self) -> Capability:
        """获取能力描述"""
        return self._capability
    
    @property
    def name(self) -> str:
        """获取数据源名称（唯一标识）"""
        return self._metadata.name
    
    @property
    def display_name(self) -> str:
        """获取显示名称"""
        return self._metadata.display_name
    
    def validate_symbol(self, symbol: str) -> bool:
        """验证交易对是否被支持"""
        supported = self.get_supported_symbols()
        if not supported:
            # 如果没有限制，认为支持
            return True
        return symbol in supported
    
    def validate_granularity(self, bar: str) -> bool:
        """验证粒度是否被支持"""
        return bar in self._capability.candlestick_granularities
    
    def get_closest_granularity(self, bar: str) -> Optional[str]:
        """获取最接近的支持粒度"""
        return Granularity.find_closest_supported(
            bar,
            self._capability.candlestick_granularities
        )


class PluginError(Exception):
    """插件相关错误"""
    pass


class PluginValidationError(PluginError):
    """插件验证错误"""
    pass
