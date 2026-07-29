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
import logging

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """数据源类型"""
    EXCHANGE = "exchange"          # 交易所
    AGGREGATOR = "aggregator"      # 数据聚合器
    CHARTING = "charting"          # 制图工具


class SymbolMode(Enum):
    """交易对模式"""
    SPOT = "spot"
    CONTRACT = "contract"
    OPTION = "option"


class Granularity:
    """标准协议粒度定义
    
    所有数据源插件必须遵循此标准粒度协议。
    插件可以选择性实现部分粒度，但必须使用标准名称。
    
    粒度映射关系：
    - 1M (月线) = 4w = 30d (近似)
    - 1w (周线) = 7d
    """
    
    # 标准粒度到秒数的映射
    GRANULARITIES = {
        "tick": 0,          # 分时（实时tick数据，特殊值）
        "1s": 1,            # 1秒
        "5s": 5,            # 5秒
        "15s": 15,          # 15秒
        "30s": 30,          # 30秒
        "1m": 60,           # 1分钟
        "3m": 180,          # 3分钟
        "5m": 300,          # 5分钟
        "10m": 600,         # 10分钟
        "15m": 900,         # 15分钟
        "30m": 1800,        # 30分钟
        "1h": 3600,         # 1小时
        "2h": 7200,         # 2小时
        "4h": 14400,        # 4小时
        "6h": 21600,        # 6小时
        "12h": 43200,       # 12小时
        "1d": 86400,        # 1天
        "2d": 172800,       # 2天
        "3d": 259200,       # 3天
        "1w": 604800,       # 1周 = 7天
        "1M": 2592000,      # 1月 = 30天 (近似)
    }
    
    # 粒度优先级（按时间从小到大，用于查找最接近的粒度）
    PRIORITY = [
        "tick", "1s", "5s", "15s", "30s",
        "1m", "3m", "5m", "10m", "15m", "30m",
        "1h", "2h", "4h", "6h", "12h",
        "1d", "2d", "3d", "1w", "1M"
    ]
    
    # 推荐粒度（常用粒度，建议插件优先实现）
    RECOMMENDED = ["1s", "1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
    
    @classmethod
    def is_valid(cls, bar: str) -> bool:
        """检查是否是有效的标准粒度"""
        return bar in cls.GRANULARITIES
    
    @classmethod
    def validate_list(cls, granularities: List[str]) -> tuple:
        """验证粒度列表，返回 (是否全部有效, 无效的粒度列表)"""
        invalid = [g for g in granularities if g not in cls.GRANULARITIES]
        return len(invalid) == 0, invalid
    
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
    symbol_modes: List[str] = field(default_factory=lambda: [SymbolMode.SPOT.value])
    
    # 其他特性
    requires_api_key: bool = False
    requires_authentication: bool = False
    requires_proxy: bool = False  # 是否需要代理访问
    has_rate_limit: bool = False
    rate_limit_per_minute: Optional[int] = None
    
    # 额外特性
    supports_real_time: bool = False
    supports_websocket: bool = False
    
    # 衍生品指标
    supports_funding_rate: bool = False
    funding_rate_interval_hours: Optional[int] = None
    funding_rate_quote_currency: Optional[str] = None
    supports_contract_basis: bool = False
    contract_basis_types: List[str] = field(default_factory=list)
    contract_basis_tenors: List[str] = field(default_factory=list)
    
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
            'symbol_modes': self.symbol_modes,
            'requires_api_key': self.requires_api_key,
            'requires_authentication': self.requires_authentication,
            'requires_proxy': self.requires_proxy,
            'has_rate_limit': self.has_rate_limit,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'supports_real_time': self.supports_real_time,
            'supports_websocket': self.supports_websocket,
            'supports_funding_rate': self.supports_funding_rate,
            'funding_rate_interval_hours': self.funding_rate_interval_hours,
            'funding_rate_quote_currency': self.funding_rate_quote_currency,
            'supports_contract_basis': self.supports_contract_basis,
            'contract_basis_types': self.contract_basis_types,
            'contract_basis_tenors': self.contract_basis_tenors,
        }

    def __post_init__(self) -> None:
        if not self.symbol_modes:
            self.symbol_modes = [SymbolMode.SPOT.value]
        normalized = []
        for mode in self.symbol_modes:
            normalized_mode = (mode or SymbolMode.SPOT.value).lower()
            normalized.append(normalized_mode)
        seen: List[str] = []
        for mode in normalized:
            if mode not in seen:
                seen.append(mode)
        self.symbol_modes = seen


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
    volume_24h: Optional[float] = None
    market_cap: Optional[float] = None  # 总市值（美元）
    market_cap_rank: Optional[int] = None  # 总市值排名
    
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
            'volume_24h': self.volume_24h,
            'market_cap': self.market_cap,
            'market_cap_rank': self.market_cap_rank,
        }


@dataclass
class FundingRateData:
    """资金费率指标"""
    inst_id: str  # 交易对（标准格式）
    funding_rate: float  # 当前资金费率，单位：百分比（如 0.0005 表示 0.05%）
    timestamp: Optional[int] = None  # 当前费率对应的时间（秒）
    funding_interval_hours: Optional[int] = None  # 资金费率结算周期
    next_funding_time: Optional[int] = None  # 下次结算时间（秒）
    predicted_funding_rate: Optional[float] = None  # 预测资金费率
    index_price: Optional[float] = None  # 指数价格 / 基准价格
    premium_index: Optional[float] = None  # 溢价指数
    quote_currency: Optional[str] = None  # 结算货币
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'inst_id': self.inst_id,
            'funding_rate': self.funding_rate,
            'timestamp': self.timestamp,
            'funding_interval_hours': self.funding_interval_hours,
            'next_funding_time': self.next_funding_time,
            'predicted_funding_rate': self.predicted_funding_rate,
            'index_price': self.index_price,
            'premium_index': self.premium_index,
            'quote_currency': self.quote_currency,
        }


@dataclass
class ContractBasisData:
    """合约基差指标"""
    inst_id: str  # 合约交易对（标准格式）
    contract_type: str  # 合约类型，如 perpetual/current_quarter
    basis: float  # 绝对基差（合约价 - 现货价）
    timestamp: Optional[int] = None  # 数据时间
    basis_rate: Optional[float] = None  # 相对基差（基差 / 现货价）
    contract_price: Optional[float] = None  # 合约价格
    reference_symbol: Optional[str] = None  # 基准标的（如现货）
    reference_price: Optional[float] = None  # 基准标的价格
    tenor: Optional[str] = None  # 到期类型，如 current_quarter
    quote_currency: Optional[str] = None  # 计价货币
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'inst_id': self.inst_id,
            'contract_type': self.contract_type,
            'basis': self.basis,
            'timestamp': self.timestamp,
            'basis_rate': self.basis_rate,
            'contract_price': self.contract_price,
            'reference_symbol': self.reference_symbol,
            'reference_price': self.reference_price,
            'tenor': self.tenor,
            'quote_currency': self.quote_currency,
        }


@dataclass
class OptionInstrument:
    """期权合约信息"""
    inst_id: str          # 合约ID，如 BTC-USD-260728-59000-C
    uly: str              # 标的资产，如 BTC-USD
    opt_type: str         # C=看涨, P=看跌
    strike: float         # 行权价
    exp_time: int         # 到期时间（秒）
    ct_val: float         # 合约面值
    ct_mult: str          # 合约乘数
    settle_currency: str  # 结算币种
    ticker: Optional[dict] = None  # 最新行情

    def to_dict(self) -> dict:
        return {
            'inst_id': self.inst_id,
            'uly': self.uly,
            'opt_type': self.opt_type,
            'strike': self.strike,
            'exp_time': self.exp_time,
            'ct_val': self.ct_val,
            'ct_mult': self.ct_mult,
            'settle_currency': self.settle_currency,
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
        
        # 验证注册的粒度是否符合标准协议
        if self._capability.supports_candlesticks:
            is_valid, invalid_granularities = Granularity.validate_list(
                self._capability.candlestick_granularities
            )
            if not is_valid:
                logger.warning(
                    f"⚠️ 插件 {self._metadata.name} 注册了非标准粒度: {', '.join(invalid_granularities)}\n"
                    f"   标准粒度: {', '.join(Granularity.PRIORITY)}"
                )
    
    @abstractmethod
    def _get_metadata(self) -> DataSourceMetadata:
        """获取数据源元数据（由子类实现）"""
        pass
    
    @abstractmethod
    def _get_capability(self) -> Capability:
        """获取数据源能力（由子类实现）"""
        pass
    
    def _normalize_symbol(self, symbol: str, mode: str = SymbolMode.SPOT.value) -> str:
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
    
    def _can_aggregate_granularity(self, requested: str, available: str) -> bool:
        """检查是否可以通过聚合细粒度数据得到粗粒度数据
        
        Args:
            requested: 请求的粒度（如 "30m"）
            available: 可用的细粒度（如 "15m"）
        
        Returns:
            是否可以聚合
        """
        requested_seconds = Granularity.to_seconds(requested)
        available_seconds = Granularity.to_seconds(available)
        
        if not requested_seconds or not available_seconds:
            return False
        
        # 请求的粒度必须是可用粒度的整数倍，且至少是2倍
        if requested_seconds % available_seconds == 0 and requested_seconds >= available_seconds * 2:
            return True
        
        return False
    
    def _find_aggregatable_granularity(self, requested: str) -> Optional[str]:
        """找到可以聚合成请求粒度的最佳细粒度
        
        Args:
            requested: 请求的粒度（如 "30m"）
        
        Returns:
            可用的细粒度，如果没有则返回 None
        """
        supported = self._capability.candlestick_granularities
        
        # 优先查找能整除的最大细粒度
        candidates = []
        for bar in supported:
            if self._can_aggregate_granularity(requested, bar):
                candidates.append((bar, Granularity.to_seconds(bar)))
        
        if not candidates:
            return None
        
        # 返回秒数最大的（最接近请求粒度的细粒度）
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    def _merge_candles(self, candles: List[CandleData]) -> CandleData:
        """合并多根蜡烛为一根
        
        OHLCV 合并规则：
        - open: 第一根的开盘价
        - high: 所有的最高价
        - low: 所有的最低价
        - close: 最后一根的收盘价
        - volume: 所有的成交量之和
        - time: 第一根的时间（作为周期起始）
        """
        if not candles:
            raise ValueError("candles 列表不能为空")
        
        if len(candles) == 1:
            return candles[0]
        
        return CandleData(
            time=candles[0].time,
            open=candles[0].open,
            high=max(c.high for c in candles),
            low=min(c.low for c in candles),
            close=candles[-1].close,
            volume=sum(c.volume for c in candles)
        )
    
    def _aggregate_candles(
        self,
        candles: List[CandleData],
        from_bar: str,
        to_bar: str
    ) -> List[CandleData]:
        """将细粒度蜡烛聚合为粗粒度蜡烛
        
        Args:
            candles: 细粒度蜡烛列表
            from_bar: 源粒度（如 "15m"）
            to_bar: 目标粒度（如 "30m"）
        
        Returns:
            聚合后的粗粒度蜡烛列表
        """
        if not candles:
            return []
        
        from_seconds = Granularity.to_seconds(from_bar)
        to_seconds = Granularity.to_seconds(to_bar)
        
        if not from_seconds or not to_seconds:
            raise ValueError(f"无效的粒度: {from_bar} 或 {to_bar}")
        
        if to_seconds % from_seconds != 0:
            raise ValueError(f"目标粒度 {to_bar} 不是源粒度 {from_bar} 的整数倍")
        
        # 按目标粒度分组
        groups = {}
        for candle in candles:
            # 计算该蜡烛属于哪个目标周期
            period_start = (candle.time // to_seconds) * to_seconds
            if period_start not in groups:
                groups[period_start] = []
            groups[period_start].append(candle)
        
        # 合并每组蜡烛
        result = []
        for period_start in sorted(groups.keys()):
            merged = self._merge_candles(groups[period_start])
            merged.time = period_start  # 使用周期起始时间
            result.append(merged)
        
        return result

    def _normalize_symbol_mode(self, mode: Optional[str]) -> str:
        normalized = (mode or SymbolMode.SPOT.value).lower()
        if normalized not in {SymbolMode.SPOT.value, SymbolMode.CONTRACT.value}:
            raise PluginError(f"未知交易模式: {mode}")
        return normalized

    def _ensure_mode_supported(self, mode: Optional[str]) -> str:
        normalized = self._normalize_symbol_mode(mode)
        if normalized not in self._capability.symbol_modes:
            raise PluginError(
                f"数据源 {self._metadata.name} 不支持交易模式 {normalized}"
            )
        return normalized
    
    @abstractmethod
    def _get_candlesticks_impl(
        self,
        symbol: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
        mode: str = SymbolMode.SPOT.value,
    ) -> List[CandleData]:
        """获取 K线数据的内部实现（由子类实现，使用数据源格式）"""
        pass
    
    @abstractmethod
    def _get_ticker_impl(self, symbol: str, mode: str = SymbolMode.SPOT.value) -> TickerData:
        """获取行情数据的内部实现（由子类实现，使用数据源格式）"""
        pass
    
    def _get_funding_rate_impl(self, symbol: str) -> FundingRateData:
        """获取资金费率的内部实现（可选，使用数据源格式）"""
        raise PluginError(
            f"数据源 {self._metadata.name} 未实现资金费率获取接口"
        )
    
    def _get_contract_basis_impl(
        self,
        symbol: str,
        contract_type: str,
        reference_symbol: Optional[str] = None,
        tenor: Optional[str] = None,
    ) -> ContractBasisData:
        """获取合约基差的内部实现（可选，使用数据源格式）"""
        raise PluginError(
            f"数据源 {self._metadata.name} 未实现合约基差获取接口"
        )
    
    def get_candlesticks(
        self,
        symbol: str,
        bar: str,
        limit: int = 100,
        before: Optional[int] = None,
        mode: str = SymbolMode.SPOT.value,
    ) -> List[CandleData]:
        """
        获取 K线数据（统一接口，支持自动粒度聚合）
        
        Args:
            symbol: 交易对（标准格式："BTCUSDT"）
            bar: 时间粒度（标准格式："1h", "1d"）
            limit: 返回条数
            before: 之前的 Unix 时间戳（秒）
        
        Returns:
            K线数据列表（时间戳已标准化为秒）
        
        Raises:
            PluginError: 如果数据源不支持或发生错误
        
        说明：
            如果数据源不直接支持请求的粒度，但支持更细的粒度，
            将自动获取细粒度数据并聚合为请求的粒度。
            例如：请求 10m，数据源只有 5m，则获取 5m 数据并合并。
        """
        mode = self._ensure_mode_supported(mode)

        # 检查是否直接支持该粒度
        if bar in self._capability.candlestick_granularities:
            # 直接支持，正常获取
            source_symbol = self._normalize_symbol(symbol, mode)
            source_bar = self._normalize_granularity(bar)
            source_before = self._normalize_timestamp(before)
            
            candles = self._get_candlesticks_impl(
                source_symbol,
                source_bar,
                limit,
                source_before,
                mode=mode,
            )
            
            # 确保时间戳标准化
            for candle in candles:
                candle.time = self._denormalize_timestamp(candle.time)
            
            return candles
        
        # 不直接支持，尝试找到可聚合的细粒度
        fine_bar = self._find_aggregatable_granularity(bar)
        
        if not fine_bar:
            raise PluginError(
                f"数据源 {self._metadata.name} 不支持粒度 {bar}，"
                f"支持的粒度: {', '.join(self._capability.candlestick_granularities)}"
            )
        
        # 计算需要获取的细粒度数据条数
        requested_seconds = Granularity.to_seconds(bar)
        fine_seconds = Granularity.to_seconds(fine_bar)
        ratio = requested_seconds // fine_seconds
        
        # 需要获取更多的细粒度数据以聚合为足够的粗粒度数据
        fine_limit = limit * ratio
        
        logger.info(
            f"📊 粒度聚合: {self._metadata.name} 不支持 {bar}，"
            f"使用 {fine_bar} 数据聚合 (获取 {fine_limit} 条)"
        )
        
        # 获取细粒度数据
        source_symbol = self._normalize_symbol(symbol, mode)
        source_fine_bar = self._normalize_granularity(fine_bar)
        source_before = self._normalize_timestamp(before)
        
        fine_candles = self._get_candlesticks_impl(
            source_symbol, 
            source_fine_bar, 
            fine_limit, 
            source_before,
            mode=mode,
        )
        
        # 标准化时间戳
        for candle in fine_candles:
            candle.time = self._denormalize_timestamp(candle.time)
        
        # 聚合为请求的粒度
        aggregated_candles = self._aggregate_candles(fine_candles, fine_bar, bar)
        
        # 限制返回数量
        return aggregated_candles[-limit:] if len(aggregated_candles) > limit else aggregated_candles
    
    def get_ticker(self, symbol: str, mode: str = SymbolMode.SPOT.value) -> TickerData:
        """
        获取最新行情数据（统一接口）
        
        Args:
            symbol: 交易对（标准格式："BTCUSDT"）
        
        Returns:
            行情数据
        
        Raises:
            PluginError: 如果数据源不支持或发生错误
        """
        mode = self._ensure_mode_supported(mode)
        # 转换为数据源格式
        source_symbol = self._normalize_symbol(symbol, mode)
        
        # 调用子类实现
        ticker = self._get_ticker_impl(source_symbol, mode)
        
        # 标准化交易对名称
        ticker.inst_id = symbol
        
        return ticker
    
    def get_funding_rate(self, symbol: str) -> FundingRateData:
        """获取指定合约的资金费率"""
        if not self._capability.supports_funding_rate:
            raise PluginError(
                f"数据源 {self._metadata.name} 未声明资金费率能力"
            )
        self._ensure_mode_supported(SymbolMode.CONTRACT.value)
        source_symbol = self._normalize_symbol(symbol, SymbolMode.CONTRACT.value)
        funding = self._get_funding_rate_impl(source_symbol)
        funding.inst_id = symbol
        if (
            funding.funding_interval_hours is None
            and self._capability.funding_rate_interval_hours is not None
        ):
            funding.funding_interval_hours = self._capability.funding_rate_interval_hours
        if (
            funding.quote_currency is None
            and self._capability.funding_rate_quote_currency is not None
        ):
            funding.quote_currency = self._capability.funding_rate_quote_currency
        return funding
    
    def get_contract_basis(
        self,
        symbol: str,
        contract_type: str = "perpetual",
        reference_symbol: Optional[str] = None,
        tenor: Optional[str] = None,
    ) -> ContractBasisData:
        """获取指定合约与基准标的之间的基差"""
        if not self._capability.supports_contract_basis:
            raise PluginError(
                f"数据源 {self._metadata.name} 未声明合约基差能力"
            )
        self._ensure_mode_supported(SymbolMode.CONTRACT.value)
        source_symbol = self._normalize_symbol(symbol, SymbolMode.CONTRACT.value)
        source_reference_symbol = (
            self._normalize_symbol(reference_symbol, SymbolMode.CONTRACT.value)
            if reference_symbol is not None
            else None
        )
        basis = self._get_contract_basis_impl(
            symbol=source_symbol,
            contract_type=contract_type,
            reference_symbol=source_reference_symbol,
            tenor=tenor,
        )
        basis.inst_id = symbol
        if reference_symbol and not basis.reference_symbol:
            basis.reference_symbol = reference_symbol
        return basis
    
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
