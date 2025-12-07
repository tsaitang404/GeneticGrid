"""
标准化数据缓存服务

统一的缓存架构，支持多种数据类型：
- K线数据 (Candlestick)
- 资金费率 (Funding Rate)
- 合约基差 (Contract Basis)
- Ticker数据

使用Redis作为主要缓存层，支持：
- 单值缓存（普通key-value）
- 时间序列缓存（sorted set）
- 自动过期（TTL）
- 批量操作
"""
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from django.conf import settings

from .redis_cache import get_redis_client, redis_cache_enabled

try:
    from redis.exceptions import RedisError
except Exception:
    class RedisError(Exception):
        pass

logger = logging.getLogger(__name__)


class CacheDataType(Enum):
    """缓存数据类型"""
    CANDLESTICK = "candles"
    FUNDING_RATE = "funding_rate"
    FUNDING_HISTORY = "funding_history"
    CONTRACT_BASIS = "basis"
    BASIS_HISTORY = "basis_history"
    TICKER = "ticker"


@dataclass
class CacheConfig:
    """缓存配置"""
    ttl: int  # 过期时间（秒）
    max_entries: Optional[int] = None  # 时间序列最大条目数
    key_prefix: str = ""  # key前缀
    
    @classmethod
    def for_type(cls, data_type: CacheDataType) -> 'CacheConfig':
        """根据数据类型返回默认配置"""
        configs = {
            CacheDataType.CANDLESTICK: cls(ttl=86400, max_entries=5000, key_prefix="candles"),
            CacheDataType.FUNDING_RATE: cls(ttl=3600, key_prefix="funding_rate"),
            CacheDataType.FUNDING_HISTORY: cls(ttl=86400, max_entries=200, key_prefix="funding_history"),
            CacheDataType.CONTRACT_BASIS: cls(ttl=1800, key_prefix="basis"),
            CacheDataType.BASIS_HISTORY: cls(ttl=3600, max_entries=1000, key_prefix="basis_history"),
            CacheDataType.TICKER: cls(ttl=30, key_prefix="ticker"),
        }
        return configs.get(data_type, cls(ttl=3600))


class BaseCacheService(ABC):
    """缓存服务基类"""
    
    def __init__(self, data_type: CacheDataType, config: Optional[CacheConfig] = None):
        self.data_type = data_type
        self.config = config or CacheConfig.for_type(data_type)
        
    @staticmethod
    def _redis_client():
        """获取Redis客户端"""
        if not redis_cache_enabled():
            return None
        return get_redis_client()
    
    @abstractmethod
    def build_key(self, **params) -> str:
        """构建缓存key"""
        pass
    
    def get(self, **params) -> Optional[Any]:
        """从缓存获取数据"""
        client = self._redis_client()
        if not client:
            return None
        
        key = self.build_key(**params)
        try:
            data = client.get(key)
            if data:
                logger.debug(f"✅ 缓存命中: {key}")
                return json.loads(data)
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"读取缓存失败 {key}: {e}")
        return None
    
    def set(self, data: Any, **params) -> bool:
        """保存数据到缓存"""
        client = self._redis_client()
        if not client:
            return False
        
        key = self.build_key(**params)
        try:
            serialized = json.dumps(data, separators=(',', ':'))
            client.setex(key, self.config.ttl, serialized)
            logger.debug(f"💾 已缓存: {key} (TTL={self.config.ttl}s)")
            return True
        except (RedisError, TypeError) as e:
            logger.error(f"保存缓存失败 {key}: {e}")
            return False
    
    def delete(self, **params) -> bool:
        """删除缓存"""
        client = self._redis_client()
        if not client:
            return False
        
        key = self.build_key(**params)
        try:
            client.delete(key)
            logger.debug(f"🗑️  已删除缓存: {key}")
            return True
        except RedisError as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            return False


class TimeSeriesCacheService(BaseCacheService):
    """时间序列缓存服务（使用sorted set）"""
    
    def get_series(self, **params) -> Optional[List[Dict[str, Any]]]:
        """获取时间序列数据"""
        client = self._redis_client()
        if not client:
            return None
        
        key = self.build_key(**params)
        try:
            data = client.zrange(key, 0, -1)
            if data:
                logger.debug(f"✅ 时间序列缓存命中: {key}, {len(data)}条")
                return [json.loads(item) for item in data]
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"读取时间序列缓存失败 {key}: {e}")
        return None
    
    def set_series(self, series_data: List[Dict[str, Any]], **params) -> bool:
        """保存时间序列数据"""
        client = self._redis_client()
        if not client or not series_data:
            return False
        
        key = self.build_key(**params)
        try:
            pipe = client.pipeline(transaction=False)
            
            # 清空旧数据
            pipe.delete(key)
            
            # 添加所有数据点，使用timestamp作为score
            for item in series_data:
                score = item.get('timestamp') or item.get('time', 0)
                serialized = json.dumps(item, separators=(',', ':'))
                pipe.zadd(key, {serialized: score})
            
            # 设置过期时间
            pipe.expire(key, self.config.ttl)
            pipe.execute()
            
            # 修剪过长的序列
            if self.config.max_entries:
                self._trim_series(client, key)
            
            logger.debug(f"💾 已缓存时间序列: {key}, {len(series_data)}条 (TTL={self.config.ttl}s)")
            return True
        except (RedisError, TypeError) as e:
            logger.error(f"保存时间序列缓存失败 {key}: {e}")
            return False
    
    def _trim_series(self, client, key: str) -> None:
        """修剪过长的时间序列，保留最新的N条"""
        try:
            size = client.zcard(key)
            if size > self.config.max_entries:
                # 删除最旧的数据
                remove_count = size - self.config.max_entries
                client.zremrangebyrank(key, 0, remove_count - 1)
                logger.debug(f"🔧 修剪时间序列 {key}: 删除最旧的{remove_count}条")
        except RedisError as e:
            logger.warning(f"修剪时间序列失败 {key}: {e}")
    
    def append_to_series(self, item: Dict[str, Any], **params) -> bool:
        """追加单条数据到时间序列"""
        client = self._redis_client()
        if not client:
            return False
        
        key = self.build_key(**params)
        try:
            score = item.get('timestamp') or item.get('time', 0)
            serialized = json.dumps(item, separators=(',', ':'))
            
            pipe = client.pipeline(transaction=False)
            pipe.zadd(key, {serialized: score})
            pipe.expire(key, self.config.ttl)
            pipe.execute()
            
            # 修剪
            if self.config.max_entries:
                self._trim_series(client, key)
            
            logger.debug(f"➕ 追加到时间序列: {key}")
            return True
        except (RedisError, TypeError) as e:
            logger.error(f"追加时间序列失败 {key}: {e}")
            return False


# ===== 具体实现 =====

class CandlestickCache(TimeSeriesCacheService):
    """K线数据缓存"""
    
    def __init__(self):
        super().__init__(CacheDataType.CANDLESTICK)
    
    def build_key(self, source: str, symbol: str, bar: str, mode: str = 'spot', **kwargs) -> str:
        return f"{self.config.key_prefix}:{source.lower()}:{symbol.upper()}:{mode.lower()}:{bar.lower()}"


class FundingRateCache(BaseCacheService):
    """资金费率当前值缓存"""
    
    def __init__(self):
        super().__init__(CacheDataType.FUNDING_RATE)
    
    def build_key(self, source: str, symbol: str, **kwargs) -> str:
        return f"{self.config.key_prefix}:{source.lower()}:{symbol.upper()}"


class FundingHistoryCache(TimeSeriesCacheService):
    """资金费率历史缓存"""
    
    def __init__(self):
        super().__init__(CacheDataType.FUNDING_HISTORY)
    
    def build_key(self, source: str, symbol: str, **kwargs) -> str:
        return f"{self.config.key_prefix}:{source.lower()}:{symbol.upper()}"


class ContractBasisCache(BaseCacheService):
    """合约基差当前值缓存"""
    
    def __init__(self):
        super().__init__(CacheDataType.CONTRACT_BASIS)
    
    def build_key(self, source: str, symbol: str, contract_type: str = 'perpetual', **kwargs) -> str:
        return f"{self.config.key_prefix}:{source.lower()}:{symbol.upper()}:{contract_type.lower()}"


class BasisHistoryCache(TimeSeriesCacheService):
    """合约基差历史缓存"""
    
    def __init__(self):
        super().__init__(CacheDataType.BASIS_HISTORY)
    
    def build_key(self, source: str, symbol: str, contract_type: str = 'perpetual', **kwargs) -> str:
        return f"{self.config.key_prefix}:{source.lower()}:{symbol.upper()}:{contract_type.lower()}"


class TickerCache(BaseCacheService):
    """Ticker数据缓存"""
    
    def __init__(self):
        super().__init__(CacheDataType.TICKER)
    
    def build_key(self, source: str, symbol: str, mode: str = 'spot', **kwargs) -> str:
        return f"{self.config.key_prefix}:{source.lower()}:{symbol.upper()}:{mode.lower()}"


# ===== 统一缓存管理器 =====

class UnifiedCacheManager:
    """统一缓存管理器"""
    
    def __init__(self):
        self.candlestick = CandlestickCache()
        self.funding_rate = FundingRateCache()
        self.funding_history = FundingHistoryCache()
        self.basis = ContractBasisCache()
        self.basis_history = BasisHistoryCache()
        self.ticker = TickerCache()
    
    def clear_all(self, pattern: Optional[str] = None) -> int:
        """清除所有缓存或匹配特定模式的缓存"""
        client = BaseCacheService._redis_client()
        if not client:
            return 0
        
        try:
            if pattern:
                keys = client.keys(pattern)
            else:
                # 清除所有数据类型的缓存
                patterns = [
                    'candles:*',
                    'funding_rate:*',
                    'funding_history:*',
                    'basis:*',
                    'basis_history:*',
                    'ticker:*'
                ]
                keys = []
                for p in patterns:
                    keys.extend(client.keys(p))
            
            if keys:
                deleted = client.delete(*keys)
                logger.info(f"🗑️  已清除 {deleted} 个缓存条目")
                return deleted
            return 0
        except RedisError as e:
            logger.error(f"清除缓存失败: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        client = BaseCacheService._redis_client()
        if not client:
            return {}
        
        try:
            stats = {}
            for data_type in CacheDataType:
                config = CacheConfig.for_type(data_type)
                pattern = f"{config.key_prefix}:*"
                keys = client.keys(pattern)
                stats[data_type.value] = len(keys)
            return stats
        except RedisError as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}


# 全局单例
_cache_manager = None

def get_cache_manager() -> UnifiedCacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = UnifiedCacheManager()
    return _cache_manager
