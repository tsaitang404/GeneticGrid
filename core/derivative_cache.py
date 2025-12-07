"""
资金费率和合约基差数据缓存服务

提供对资金费率和合约基差历史数据的缓存支持，减轻API负担。
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from django.conf import settings

from .redis_cache import get_redis_client, redis_cache_enabled

try:
    from redis.exceptions import RedisError
except Exception:
    class RedisError(Exception):
        pass

logger = logging.getLogger(__name__)


class DerivativeDataCacheService:
    """衍生品数据缓存服务 - 资金费率和合约基差"""
    
    # Redis缓存配置
    _redis_ttl_funding_rate = 3600  # 资金费率缓存1小时
    _redis_ttl_basis = 1800  # 基差缓存30分钟
    _redis_ttl_funding_history = 86400  # 资金费率历史缓存1天
    _redis_ttl_basis_history = 3600  # 基差历史缓存1小时
    
    @staticmethod
    def _redis_client():
        """获取Redis客户端"""
        if not redis_cache_enabled():
            return None
        return get_redis_client()
    
    @staticmethod
    def _redis_key_funding_rate(source: str, symbol: str) -> str:
        """资金费率当前值的Redis key"""
        return f"funding_rate:{source.lower()}:{symbol.upper()}"
    
    @staticmethod
    def _redis_key_funding_history(source: str, symbol: str) -> str:
        """资金费率历史数据的Redis key"""
        return f"funding_history:{source.lower()}:{symbol.upper()}"
    
    @staticmethod
    def _redis_key_basis(source: str, symbol: str, contract_type: str) -> str:
        """合约基差当前值的Redis key"""
        return f"basis:{source.lower()}:{symbol.upper()}:{contract_type.lower()}"
    
    @staticmethod
    def _redis_key_basis_history(source: str, symbol: str, contract_type: str) -> str:
        """合约基差历史数据的Redis key"""
        return f"basis_history:{source.lower()}:{symbol.upper()}:{contract_type.lower()}"
    
    # ===== 资金费率缓存 =====
    
    @staticmethod
    def get_funding_rate_from_cache(source: str, symbol: str) -> Optional[Dict[str, Any]]:
        """从缓存获取资金费率当前值"""
        client = DerivativeDataCacheService._redis_client()
        if not client:
            return None
        
        key = DerivativeDataCacheService._redis_key_funding_rate(source, symbol)
        try:
            data = client.get(key)
            if data:
                logger.debug(f"资金费率缓存命中: {key}")
                return json.loads(data)
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"读取资金费率缓存失败: {e}")
        return None
    
    @staticmethod
    def save_funding_rate_to_cache(source: str, symbol: str, data: Dict[str, Any]) -> None:
        """保存资金费率当前值到缓存"""
        client = DerivativeDataCacheService._redis_client()
        if not client:
            logger.warning("Redis客户端不可用，跳过缓存")
            return
        
        key = DerivativeDataCacheService._redis_key_funding_rate(source, symbol)
        try:
            serialized = json.dumps(data, separators=(',', ':'))
            logger.info(f"准备写入Redis: key={key}, data_len={len(serialized)}")
            
            client.setex(
                key,
                DerivativeDataCacheService._redis_ttl_funding_rate,
                serialized
            )
            logger.info(f"✅ 资金费率已缓存: {key}")
        except (RedisError, TypeError) as e:
            logger.error(f"❌ 保存资金费率缓存失败: {e}")
    
    @staticmethod
    def get_funding_history_from_cache(source: str, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """从缓存获取资金费率历史数据"""
        client = DerivativeDataCacheService._redis_client()
        if not client:
            return None
        
        key = DerivativeDataCacheService._redis_key_funding_history(source, symbol)
        try:
            # 使用sorted set存储历史数据，按时间戳排序
            data = client.zrange(key, 0, -1)
            if data:
                logger.debug(f"资金费率历史缓存命中: {key}, {len(data)}条")
                return [json.loads(item) for item in data]
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"读取资金费率历史缓存失败: {e}")
        return None
    
    @staticmethod
    def save_funding_history_to_cache(source: str, symbol: str, history: List[Dict[str, Any]]) -> None:
        """保存资金费率历史数据到缓存"""
        client = DerivativeDataCacheService._redis_client()
        if not client or not history:
            return
        
        key = DerivativeDataCacheService._redis_key_funding_history(source, symbol)
        try:
            pipe = client.pipeline(transaction=False)
            
            # 清空旧数据
            pipe.delete(key)
            
            # 添加所有历史记录，使用时间戳作为score
            for item in history:
                score = item.get('timestamp', 0)
                serialized = json.dumps(item, separators=(',', ':'))
                pipe.zadd(key, {serialized: score})
            
            # 设置过期时间
            pipe.expire(key, DerivativeDataCacheService._redis_ttl_funding_history)
            pipe.execute()
            
            logger.debug(f"资金费率历史已缓存: {key}, {len(history)}条")
        except (RedisError, TypeError) as e:
            logger.warning(f"保存资金费率历史缓存失败: {e}")
    
    # ===== 合约基差缓存 =====
    
    @staticmethod
    def get_basis_from_cache(source: str, symbol: str, contract_type: str) -> Optional[Dict[str, Any]]:
        """从缓存获取合约基差当前值"""
        client = DerivativeDataCacheService._redis_client()
        if not client:
            return None
        
        key = DerivativeDataCacheService._redis_key_basis(source, symbol, contract_type)
        try:
            data = client.get(key)
            if data:
                logger.debug(f"合约基差缓存命中: {key}")
                return json.loads(data)
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"读取合约基差缓存失败: {e}")
        return None
    
    @staticmethod
    def save_basis_to_cache(source: str, symbol: str, contract_type: str, data: Dict[str, Any]) -> None:
        """保存合约基差当前值到缓存"""
        client = DerivativeDataCacheService._redis_client()
        if not client:
            return
        
        key = DerivativeDataCacheService._redis_key_basis(source, symbol, contract_type)
        try:
            client.setex(
                key,
                DerivativeDataCacheService._redis_ttl_basis,
                json.dumps(data, separators=(',', ':'))
            )
            logger.debug(f"合约基差已缓存: {key}")
        except (RedisError, TypeError) as e:
            logger.warning(f"保存合约基差缓存失败: {e}")
    
    @staticmethod
    def get_basis_history_from_cache(source: str, symbol: str, contract_type: str) -> Optional[List[Dict[str, Any]]]:
        """从缓存获取合约基差历史数据"""
        client = DerivativeDataCacheService._redis_client()
        if not client:
            return None
        
        key = DerivativeDataCacheService._redis_key_basis_history(source, symbol, contract_type)
        try:
            # 检查缓存是否过期（基差历史数据应该是最近1小时内的）
            ttl = client.ttl(key)
            if ttl <= 0:
                return None
            
            data = client.zrange(key, 0, -1)
            if data:
                logger.debug(f"合约基差历史缓存命中: {key}, {len(data)}条")
                return [json.loads(item) for item in data]
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"读取合约基差历史缓存失败: {e}")
        return None
    
    @staticmethod
    def save_basis_history_to_cache(source: str, symbol: str, contract_type: str, history: List[Dict[str, Any]]) -> None:
        """保存合约基差历史数据到缓存"""
        client = DerivativeDataCacheService._redis_client()
        if not client or not history:
            return
        
        key = DerivativeDataCacheService._redis_key_basis_history(source, symbol, contract_type)
        try:
            pipe = client.pipeline(transaction=False)
            
            # 清空旧数据
            pipe.delete(key)
            
            # 添加所有历史记录
            for item in history:
                score = item.get('timestamp', 0)
                serialized = json.dumps(item, separators=(',', ':'))
                pipe.zadd(key, {serialized: score})
            
            # 设置过期时间
            pipe.expire(key, DerivativeDataCacheService._redis_ttl_basis_history)
            pipe.execute()
            
            logger.debug(f"合约基差历史已缓存: {key}, {len(history)}条")
        except (RedisError, TypeError) as e:
            logger.warning(f"保存合约基差历史缓存失败: {e}")
    
    # ===== 缓存管理 =====
    
    @staticmethod
    def clear_all_derivative_cache() -> int:
        """清除所有衍生品数据缓存"""
        client = DerivativeDataCacheService._redis_client()
        if not client:
            return 0
        
        try:
            patterns = [
                'funding_rate:*',
                'funding_history:*',
                'basis:*',
                'basis_history:*'
            ]
            
            deleted = 0
            for pattern in patterns:
                keys = client.keys(pattern)
                if keys:
                    deleted += client.delete(*keys)
            
            logger.info(f"已清除 {deleted} 个衍生品数据缓存")
            return deleted
        except RedisError as e:
            logger.error(f"清除缓存失败: {e}")
            return 0
