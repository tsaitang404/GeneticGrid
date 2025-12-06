# -*- coding: utf-8 -*-
"""
统一协议层 - 处理前端和不同数据源之间的格式转换
"""
from typing import Optional, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)


class ProtocolConverter:
    """协议转换器 - 统一前后端交互格式"""
    
    # 标准格式定义
    STANDARD_SYMBOL_FORMAT = "BTCUSDT"  # 前端使用：无分隔符
    STANDARD_TIME_UNIT = "ms"  # 统一使用毫秒
    
    # 数据源格式映射
    SOURCE_FORMATS = {
        'okx': {
            'symbol_separator': '-',  # BTC-USDT
            'symbol_format': '{base}-{quote}',
            'time_unit': 'ms',  # OKX API 使用毫秒
        },
        'binance': {
            'symbol_separator': '',  # BTCUSDT
            'symbol_format': '{base}{quote}',
            'time_unit': 'ms',  # Binance API 使用毫秒
        },
        'bybit': {
            'symbol_separator': '',  # BTCUSDT
            'symbol_format': '{base}{quote}',
            'time_unit': 'ms',  # Bybit API 使用毫秒
        },
        'coinbase': {
            'symbol_separator': '-',  # BTC-USD
            'symbol_format': '{base}-{quote}',
            'time_unit': 's',  # Coinbase API 使用秒
        },
        'kraken': {
            'symbol_separator': '',  # XBTUSDT
            'symbol_format': '{base}{quote}',
            'time_unit': 's',  # Kraken API 使用秒
            'symbol_mapping': {
                'BTC': 'XBT',  # Kraken 使用 XBT 表示 BTC
            }
        },
        'coingecko': {
            'symbol_separator': '',  # bitcoin
            'symbol_format': 'lowercase',  # 特殊处理
            'time_unit': 's',
        },
    }
    
    # 时间粒度映射（标准格式 -> 各数据源格式）
    GRANULARITY_MAPPINGS = {
        'okx': {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1H', '2h': '2H', '4h': '4H', '6h': '6H', '12h': '12H',
            '1d': '1D', '1w': '1W', '1M': '1M',
        },
        'binance': {
            'tick': '1s',
            '1s': '1s',
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h', '12h': '12h',
            '1d': '1d', '3d': '3d', '1w': '1w', '1M': '1M',
        },
        'bybit': {
            '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
            '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
            '1d': 'D', '1w': 'W', '1M': 'M',
        },
        'coinbase': {
            '1m': '60', '5m': '300', '15m': '900',
            '1h': '3600', '6h': '21600',
            '1d': '86400',
        },
        'kraken': {
            '1m': '1', '5m': '5', '15m': '15', '30m': '30',
            '1h': '60', '4h': '240',
            '1d': '1440', '1w': '10080',
        },
    }
    
    @classmethod
    def parse_symbol(cls, symbol: str) -> Dict[str, str]:
        """解析交易对，提取基础币种和计价币种
        
        支持格式：
        - BTCUSDT (标准格式)
        - BTC-USDT
        - BTC/USDT
        - XBTUSDT (Kraken)
        """
        # 移除常见分隔符
        clean_symbol = symbol.upper().replace('-', '').replace('/', '').replace('_', '')
        
        # 常见计价币种
        quote_currencies = ['USDT', 'USDC', 'USD', 'BUSD', 'EUR', 'GBP', 'BTC', 'ETH']
        
        base = None
        quote = None
        
        # 尝试匹配计价币种
        for q in quote_currencies:
            if clean_symbol.endswith(q):
                quote = q
                base = clean_symbol[:-len(q)]
                break
        
        if not base or not quote:
            # 默认假设最后4位是计价币种
            if len(clean_symbol) > 4:
                base = clean_symbol[:-4]
                quote = clean_symbol[-4:]
            else:
                raise ValueError(f"无法解析交易对格式: {symbol}")
        
        return {'base': base, 'quote': quote}
    
    @classmethod
    def to_source_symbol(cls, standard_symbol: str, source: str) -> str:
        """将标准格式的交易对转换为数据源格式
        
        Args:
            standard_symbol: 标准格式，如 "BTCUSDT"
            source: 数据源名称，如 "okx"
        
        Returns:
            数据源格式的交易对，如 "BTC-USDT"
        """
        source_config = cls.SOURCE_FORMATS.get(source, {})
        
        # 解析交易对
        parsed = cls.parse_symbol(standard_symbol)
        base = parsed['base']
        quote = parsed['quote']
        
        # 特殊处理：Kraken 的币种映射
        if source == 'kraken' and base in source_config.get('symbol_mapping', {}):
            base = source_config['symbol_mapping'][base]
        
        # 特殊处理：CoinGecko
        if source == 'coingecko':
            # CoinGecko 使用完整币名（小写）
            coin_map = {
                'BTC': 'bitcoin', 'ETH': 'ethereum', 'BNB': 'binancecoin',
                'SOL': 'solana', 'XRP': 'ripple', 'ADA': 'cardano',
                'DOGE': 'dogecoin', 'DOT': 'polkadot', 'MATIC': 'matic-network',
            }
            return coin_map.get(base, base.lower())
        
        # 应用格式
        separator = source_config.get('symbol_separator', '')
        return f"{base}{separator}{quote}"
    
    @classmethod
    def to_source_granularity(cls, standard_granularity: str, source: str) -> str:
        """将标准时间粒度转换为数据源格式
        
        Args:
            standard_granularity: 标准格式，如 "1h"
            source: 数据源名称
        
        Returns:
            数据源格式的粒度，如 OKX 的 "1H"
        """
        mapping = cls.GRANULARITY_MAPPINGS.get(source, {})
        converted = mapping.get(standard_granularity, standard_granularity)
        
        logger.debug(f"Granularity conversion: {standard_granularity} -> {converted} ({source})")
        return converted
    
    @classmethod
    def to_source_timestamp(cls, timestamp_ms: Optional[int], source: str) -> Optional[int]:
        """将标准时间戳（毫秒）转换为数据源格式
        
        Args:
            timestamp_ms: 毫秒时间戳
            source: 数据源名称
        
        Returns:
            数据源格式的时间戳
        """
        if timestamp_ms is None:
            return None
        
        source_config = cls.SOURCE_FORMATS.get(source, {})
        time_unit = source_config.get('time_unit', 'ms')
        
        if time_unit == 's':
            return timestamp_ms // 1000  # 转换为秒
        else:
            return timestamp_ms  # 保持毫秒
    
    @classmethod
    def from_source_timestamp(cls, timestamp: int, source: str) -> int:
        """将数据源时间戳转换为标准格式（毫秒）
        
        Args:
            timestamp: 数据源的时间戳
            source: 数据源名称
        
        Returns:
            毫秒时间戳
        """
        source_config = cls.SOURCE_FORMATS.get(source, {})
        time_unit = source_config.get('time_unit', 'ms')
        
        if time_unit == 's':
            return timestamp * 1000  # 秒转毫秒
        else:
            return timestamp  # 已经是毫秒
    
    @classmethod
    def normalize_request_params(cls, symbol: str, bar: str, source: str,
                                 before: Optional[int] = None,
                                 after: Optional[int] = None,
                                 limit: int = 100) -> Dict[str, Any]:
        """统一处理前端请求参数，转换为数据源格式
        
        Args:
            symbol: 前端传入的交易对（标准格式）
            bar: 时间粒度（标准格式）
            source: 数据源名称
            before: 之前的时间戳（毫秒）
            after: 之后的时间戳（毫秒）
            limit: 数量限制
        
        Returns:
            转换后的参数字典
        """
        return {
            'symbol': cls.to_source_symbol(symbol, source),
            'bar': cls.to_source_granularity(bar, source),
            'before': cls.to_source_timestamp(before, source),
            'after': cls.to_source_timestamp(after, source),
            'limit': limit,
            'source': source,
            'original_symbol': symbol,  # 保留原始格式用于缓存键
        }
    
    @classmethod
    def normalize_response_data(cls, data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """统一处理数据源返回的数据，转换为标准格式
        
        Args:
            data: 数据源返回的数据
            source: 数据源名称
        
        Returns:
            标准格式的数据
        """
        # 如果数据包含时间戳，统一转换为毫秒
        if 'time' in data and isinstance(data['time'], int):
            data['time'] = cls.from_source_timestamp(data['time'], source)
        
        # 如果是数组数据，递归处理
        if isinstance(data, list):
            return [cls.normalize_response_data(item, source) for item in data]
        
        return data
    
    @classmethod
    def get_supported_granularities(cls, source: str) -> list:
        """获取数据源支持的时间粒度列表（标准格式）
        
        Args:
            source: 数据源名称
        
        Returns:
            标准格式的粒度列表
        """
        mapping = cls.GRANULARITY_MAPPINGS.get(source, {})
        return list(mapping.keys())
    
    @classmethod
    def validate_request(cls, symbol: str, bar: str, source: str) -> tuple[bool, Optional[str]]:
        """验证请求参数是否有效
        
        Returns:
            (是否有效, 错误信息)
        """
        # 检查数据源是否支持
        if source not in cls.SOURCE_FORMATS:
            return False, f"不支持的数据源: {source}"
        
        # 检查时间粒度是否支持
        if source in cls.GRANULARITY_MAPPINGS:
            if bar not in cls.GRANULARITY_MAPPINGS[source]:
                supported = ', '.join(cls.GRANULARITY_MAPPINGS[source].keys())
                return False, f"数据源 {source} 不支持粒度 {bar}，支持的粒度: {supported}"
        
        # 尝试解析交易对
        try:
            cls.parse_symbol(symbol)
        except ValueError as e:
            return False, str(e)
        
        return True, None
