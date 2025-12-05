"""K线数据缓存服务"""
from .models import CandlestickCache
from .plugin_adapter import get_unified_service
from .services import MarketAPIError
from django.db import transaction
from django.db.utils import OperationalError
from decimal import Decimal
import logging
import time

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
    def save_to_cache(source: str, symbol: str, bar: str, candles: list, max_retries: int = 3):
        """批量保存K线数据到缓存
        
        Args:
            source: 数据源
            symbol: 交易对
            bar: 时间周期
            candles: K线数据列表
            max_retries: 最大重试次数
        """
        if not candles:
            return 0
        
        created_count = 0
        updated_count = 0
        
        for attempt in range(max_retries):
            try:
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
                
            except OperationalError as e:
                if 'database is locked' in str(e) and attempt < max_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)  # 指数退避: 0.1s, 0.2s, 0.4s
                    logger.warning(f"Database locked, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to save to cache after {attempt + 1} attempts: {e}")
                    raise
        
        return created_count
    
    @staticmethod
    def get_cache_range(source: str, symbol: str, bar: str):
        """获取缓存的数据范围（使用聚合查询优化性能）
        
        Returns:
            dict: {'oldest': timestamp, 'newest': timestamp, 'count': int}
        """
        from django.db.models import Min, Max, Count
        
        result = CandlestickCache.objects.filter(
            source=source,
            symbol=symbol,
            bar=bar
        ).aggregate(
            oldest=Min('time'),
            newest=Max('time'),
            count=Count('id')
        )
        
        return {
            'oldest': result['oldest'],
            'newest': result['newest'],
            'count': result['count'] or 0
        }
    
    @staticmethod
    def fetch_and_cache(source: str, symbol: str, bar: str, limit: int = 1000, before: int = None):
        """从API获取数据并异步缓存（不阻塞返回）
        
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
            # 使用统一服务（优先插件系统）
            service = get_unified_service(source)
            candles = service.get_candlesticks(inst_id=symbol, bar=bar, limit=limit, before=before)
            
            # 日志标记数据来源
            if service.is_using_plugin:
                logger.info(f"📦 使用插件获取 {source}/{symbol}/{bar}: {len(candles)} 条")
            else:
                logger.info(f"🔧 使用旧服务获取 {source}/{symbol}/{bar}: {len(candles)} 条")
            
            # 异步保存到缓存（不等待结果，避免阻塞）
            if candles:
                try:
                    CandlestickCacheService.save_to_cache(source, symbol, bar, candles, max_retries=1)
                except Exception as e:
                    # 缓存失败不影响数据返回
                    logger.warning(f"Failed to cache data (non-blocking): {e}")
            
            return candles
        except MarketAPIError as e:
            logger.error(f"Failed to fetch from {source}: {e}")
            raise
    
    @staticmethod
    def get_with_auto_fetch(source: str, symbol: str, bar: str, limit: int = 100,
                           before: int = None, after: int = None):
        """智能获取数据：优先从缓存获取，缓存不足时从API补充
        
        策略：
        1. 先从缓存获取数据
        2. 如果缓存数据充足（≥limit），直接返回
        3. 如果缓存数据不足，从API补充并缓存
        
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
        
        # 如果缓存数据充足，直接返回
        if len(cached_data) >= limit:
            logger.info(f"✅ Cache hit: {len(cached_data)} candles from cache")
            return cached_data
        
        # 缓存数据不足，从API获取并补充
        logger.info(f"⚠️ Cache miss or insufficient: {len(cached_data)}/{limit}, fetching from API...")
        
        try:
            # 转换before为毫秒（API需要）
            before_ms = before * 1000 if before else None
            
            # 从API获取（会自动缓存）
            api_data = CandlestickCacheService.fetch_and_cache(
                source, symbol, bar, limit, before_ms
            )
            
            # 如果有after参数，过滤数据
            if after and api_data:
                filtered_data = [c for c in api_data if c['time'] > after]
                logger.info(f"✅ API success: {len(filtered_data)} candles after {after}")
                return filtered_data
            
            logger.info(f"✅ API success: {len(api_data)} candles")
            return api_data
            
        except MarketAPIError as e:
            # API失败时，返回缓存数据（即使不足）
            if cached_data:
                logger.warning(f"⚠️ API failed, returning cached data: {len(cached_data)} candles")
                return cached_data
            else:
                logger.error(f"❌ API failed and no cached data available")
                raise
