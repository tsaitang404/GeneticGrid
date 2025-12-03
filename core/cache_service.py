"""K线数据缓存服务"""
from .models import CandlestickCache
from .services import get_market_service, MarketAPIError
from django.db import transaction
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class CandlestickCacheService:
    """K线数据缓存服务 - 负责数据库缓存的读写"""
    
    @staticmethod
    def get_from_cache(source: str, symbol: str, bar: str, limit: int = 100, 
                      before: int = None, after: int = None):
        """从缓存获取K线数据
        
        Args:
            source: 数据源
            symbol: 交易对
            bar: 时间周期
            limit: 返回数量
            before: 获取该时间戳之前的数据（秒）
            after: 获取该时间戳之后的数据（秒）
        
        Returns:
            list: K线数据列表
        """
        queryset = CandlestickCache.objects.filter(
            source=source,
            symbol=symbol,
            bar=bar
        )
        
        if before:
            queryset = queryset.filter(time__lt=before)
        
        if after:
            queryset = queryset.filter(time__gt=after)
        
        # 根据时间倒序排序，取最新的limit条
        candles = queryset.order_by('-time')[:limit]
        
        # 转换为列表并正序返回
        result = []
        for candle in reversed(list(candles)):
            result.append({
                'time': candle.time,
                'open': float(candle.open),
                'high': float(candle.high),
                'low': float(candle.low),
                'close': float(candle.close),
                'volume': float(candle.volume),
            })
        
        return result
    
    @staticmethod
    def save_to_cache(source: str, symbol: str, bar: str, candles: list):
        """批量保存K线数据到缓存
        
        Args:
            source: 数据源
            symbol: 交易对
            bar: 时间周期
            candles: K线数据列表
        """
        if not candles:
            return 0
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for candle in candles:
                obj, created = CandlestickCache.objects.update_or_create(
                    source=source,
                    symbol=symbol,
                    bar=bar,
                    time=candle['time'],
                    defaults={
                        'open': Decimal(str(candle['open'])),
                        'high': Decimal(str(candle['high'])),
                        'low': Decimal(str(candle['low'])),
                        'close': Decimal(str(candle['close'])),
                        'volume': Decimal(str(candle['volume'])),
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
        
        logger.info(f"Saved {created_count} new, updated {updated_count} candles for {source}/{symbol}/{bar}")
        return created_count
    
    @staticmethod
    def get_cache_range(source: str, symbol: str, bar: str):
        """获取缓存的数据范围
        
        Returns:
            dict: {'oldest': timestamp, 'newest': timestamp, 'count': int}
        """
        queryset = CandlestickCache.objects.filter(
            source=source,
            symbol=symbol,
            bar=bar
        )
        
        if not queryset.exists():
            return {'oldest': None, 'newest': None, 'count': 0}
        
        oldest = queryset.order_by('time').first()
        newest = queryset.order_by('-time').first()
        count = queryset.count()
        
        return {
            'oldest': oldest.time if oldest else None,
            'newest': newest.time if newest else None,
            'count': count
        }
    
    @staticmethod
    def fetch_and_cache(source: str, symbol: str, bar: str, limit: int = 1000, before: int = None):
        """从API获取数据并缓存
        
        Args:
            source: 数据源
            symbol: 交易对
            bar: 时间周期
            limit: 获取数量
            before: 获取该时间戳之前的数据（毫秒）
        
        Returns:
            list: K线数据
        """
        try:
            # 从API获取数据
            service = get_market_service(source)
            candles = service.get_candlesticks(inst_id=symbol, bar=bar, limit=limit, before=before)
            
            # 保存到缓存
            if candles:
                CandlestickCacheService.save_to_cache(source, symbol, bar, candles)
            
            return candles
        except MarketAPIError as e:
            logger.error(f"Failed to fetch from {source}: {e}")
            raise
    
    @staticmethod
    def get_with_auto_fetch(source: str, symbol: str, bar: str, limit: int = 100,
                           before: int = None, after: int = None):
        """智能获取数据：优先从缓存，缺失时从API获取并缓存
        
        Args:
            source: 数据源
            symbol: 交易对
            bar: 时间周期
            limit: 返回数量
            before: 获取该时间戳之前的数据（秒）
            after: 获取该时间戳之后的数据（秒）
        
        Returns:
            list: K线数据
        """
        # 首先尝试从缓存获取
        cached_data = CandlestickCacheService.get_from_cache(
            source, symbol, bar, limit, before, after
        )
        
        # 如果缓存数据足够，直接返回
        if len(cached_data) >= min(limit, 100):
            logger.info(f"Cache hit: {len(cached_data)} candles for {source}/{symbol}/{bar}")
            return cached_data
        
        # 缓存不足，从API获取
        logger.info(f"Cache miss or insufficient, fetching from API: {source}/{symbol}/{bar}")
        
        try:
            # 转换before为毫秒（API需要）
            before_ms = before * 1000 if before else None
            
            # 从API获取并缓存
            api_data = CandlestickCacheService.fetch_and_cache(
                source, symbol, bar, limit, before_ms
            )
            
            return api_data
        except MarketAPIError:
            # API失败时，返回缓存的数据（即使不足）
            logger.warning(f"API failed, returning cached data ({len(cached_data)} candles)")
            return cached_data
