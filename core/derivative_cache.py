"""
资金费率和合约基差数据缓存服务

使用统一缓存架构提供衍生品数据缓存。
此模块保持向后兼容的API。
"""
import logging
from typing import Any, Dict, List, Optional

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
    
    @staticmethod
    def get_funding_history_from_cache(source: str, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """从缓存获取资金费率历史数据"""
        manager = get_cache_manager()
        return manager.funding_history.get_series(source=source, symbol=symbol)
    
    @staticmethod
    def save_funding_history_to_cache(source: str, symbol: str, history: List[Dict[str, Any]]) -> None:
        """保存资金费率历史数据到缓存"""
        manager = get_cache_manager()
        manager.funding_history.set_series(history, source=source, symbol=symbol)
    
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
    
    @staticmethod
    def get_basis_history_from_cache(source: str, symbol: str, contract_type: str, granularity: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """从缓存获取合约基差历史数据
        
        Args:
            source: 数据源
            symbol: 交易对
            contract_type: 合约类型
            granularity: 时间粒度（可选，用于隔离不同粒度的缓存）
        """
        manager = get_cache_manager()
        extra_key = f":{granularity}" if granularity else ""
        return manager.basis_history.get_series(source=source, symbol=symbol, contract_type=contract_type + extra_key)
    
    @staticmethod
    def save_basis_history_to_cache(source: str, symbol: str, contract_type: str, history: List[Dict[str, Any]], granularity: Optional[str] = None) -> None:
        """保存合约基差历史数据到缓存
        
        Args:
            source: 数据源
            symbol: 交易对
            contract_type: 合约类型
            history: 历史数据
            granularity: 时间粒度（可选，用于隔离不同粒度的缓存）
        """
        manager = get_cache_manager()
        extra_key = f":{granularity}" if granularity else ""
        manager.basis_history.set_series(history, source=source, symbol=symbol, contract_type=contract_type + extra_key)
    
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

