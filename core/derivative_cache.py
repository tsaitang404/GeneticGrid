"""
资金费率和合约基差数据缓存服务

使用统一缓存架构提供衍生品数据缓存。
此模块保持向后兼容的API。
"""
import logging
from typing import Any, Dict, List, Optional

from django.db import transaction

from .models import FundingRateHistory, BasisHistory
from .unified_cache import get_cache_manager

logger = logging.getLogger(__name__)


class DerivativeDataCacheService:
    """衍生品数据缓存服务 - 向后兼容包装器"""
    
    # ===== 资金费率缓存 =====
    
    @staticmethod
    def get_funding_rate_from_cache(source: str, symbol: str) -> Optional[Dict[str, Any]]:
        """从缓存获取资金费率当前值"""
        manager = get_cache_manager()
        return manager.funding_rate.get(source=source, symbol=symbol)
    
    @staticmethod
    def save_funding_rate_to_cache(source: str, symbol: str, data: Dict[str, Any]) -> None:
        """保存资金费率当前值到缓存"""
        manager = get_cache_manager()
        manager.funding_rate.set(data, source=source, symbol=symbol)
    
    # ===== 资金费率历史 =====
    
    @staticmethod
    def get_funding_history_from_cache(source: str, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """从 Redis 缓存获取资金费率历史数据"""
        manager = get_cache_manager()
        return manager.funding_history.get_series(source=source, symbol=symbol)
    
    @staticmethod
    def get_funding_history_from_db(source: str, symbol: str, limit: int = 100, granularity: str = '8h') -> Optional[List[Dict[str, Any]]]:
        """从数据库获取资金费率历史数据"""
        try:
            qs = FundingRateHistory.objects.filter(
                source=source, symbol=symbol.upper(), granularity=granularity
            ).order_by('timestamp')[:limit]
            data = [r.to_dict() for r in qs]
            if data:
                logger.info(f"📦 资金费率历史数据库命中: {symbol}, {len(data)}条")
            return data or None
        except Exception as e:
            logger.error(f"读取资金费率历史数据库失败: {e}")
            return None
    
    @staticmethod
    def save_funding_history_to_cache(source: str, symbol: str, history: List[Dict[str, Any]]) -> None:
        """保存资金费率历史数据到 Redis 缓存"""
        manager = get_cache_manager()
        manager.funding_history.set_series(history, source=source, symbol=symbol)
    
    @staticmethod
    @transaction.atomic
    def save_funding_history_to_db(source: str, symbol: str, history: List[Dict[str, Any]], granularity: str = '8h') -> None:
        """保存资金费率历史数据到数据库（批量 upsert）"""
        if not history:
            return
        symbol = symbol.upper()
        objs = []
        for item in history:
            ts = item.get('timestamp')
            fr = item.get('funding_rate')
            if ts is None or fr is None:
                continue
            objs.append(FundingRateHistory(
                source=source,
                symbol=symbol,
                granularity=granularity,
                timestamp=ts,
                funding_rate=fr,
                realized_rate=item.get('realized_rate'),
            ))
        if objs:
            FundingRateHistory.objects.bulk_create(
                objs, ignore_conflicts=True, batch_size=500
            )
            logger.info(f"💾 资金费率历史已持久化: {symbol}, {len(objs)}条")
    
    # ===== 合约基差缓存 =====
    
    @staticmethod
    def get_basis_from_cache(source: str, symbol: str, contract_type: str) -> Optional[Dict[str, Any]]:
        """从缓存获取合约基差当前值"""
        manager = get_cache_manager()
        return manager.basis.get(source=source, symbol=symbol, contract_type=contract_type)
    
    @staticmethod
    def save_basis_to_cache(source: str, symbol: str, contract_type: str, data: Dict[str, Any]) -> None:
        """保存合约基差当前值到缓存"""
        manager = get_cache_manager()
        manager.basis.set(data, source=source, symbol=symbol, contract_type=contract_type)
    
    # ===== 合约基差历史 =====
    
    @staticmethod
    def get_basis_history_from_cache(source: str, symbol: str, contract_type: str, granularity: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """从 Redis 缓存获取合约基差历史数据"""
        manager = get_cache_manager()
        extra_key = f":{granularity}" if granularity else ""
        return manager.basis_history.get_series(source=source, symbol=symbol, contract_type=contract_type + extra_key)
    
    @staticmethod
    def get_basis_history_from_db(source: str, symbol: str, contract_type: str = 'perpetual', limit: int = 720, granularity: str = '1h') -> Optional[List[Dict[str, Any]]]:
        """从数据库获取合约基差历史数据"""
        try:
            qs = BasisHistory.objects.filter(
                source=source, symbol=symbol.upper(),
                contract_type=contract_type, granularity=granularity
            ).order_by('timestamp')[:limit]
            data = [r.to_dict() for r in qs]
            if data:
                logger.info(f"📦 基差历史数据库命中: {symbol}, {len(data)}条")
            return data or None
        except Exception as e:
            logger.error(f"读取基差历史数据库失败: {e}")
            return None
    
    @staticmethod
    def save_basis_history_to_cache(source: str, symbol: str, contract_type: str, history: List[Dict[str, Any]], granularity: Optional[str] = None) -> None:
        """保存合约基差历史数据到 Redis 缓存"""
        manager = get_cache_manager()
        extra_key = f":{granularity}" if granularity else ""
        manager.basis_history.set_series(history, source=source, symbol=symbol, contract_type=contract_type + extra_key)
    
    @staticmethod
    @transaction.atomic
    def save_basis_history_to_db(source: str, symbol: str, contract_type: str, history: List[Dict[str, Any]], granularity: str = '1h') -> None:
        """保存合约基差历史数据到数据库（批量 upsert）"""
        if not history:
            return
        symbol = symbol.upper()
        objs = []
        for item in history:
            ts = item.get('timestamp')
            basis = item.get('basis')
            if ts is None or basis is None:
                continue
            objs.append(BasisHistory(
                source=source,
                symbol=symbol,
                contract_type=contract_type,
                granularity=granularity,
                timestamp=ts,
                basis=basis,
                basis_rate=item.get('basis_rate', 0),
                contract_price=item.get('contract_price', 0),
                spot_price=item.get('spot_price', 0),
            ))
        if objs:
            BasisHistory.objects.bulk_create(
                objs, ignore_conflicts=True, batch_size=500
            )
            logger.info(f"💾 基差历史已持久化: {symbol}, {len(objs)}条")
    
    # ===== 缓存管理 =====
    
    @staticmethod
    def clear_all_derivative_cache() -> int:
        """清除所有衍生品数据缓存"""
        manager = get_cache_manager()
        deleted = 0
        for pattern in ['funding_rate:*', 'funding_history:*', 'basis:*', 'basis_history:*']:
            deleted += manager.clear_all(pattern)
        logger.info(f"已清除 {deleted} 个衍生品数据缓存")
        return deleted

