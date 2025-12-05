# -*- coding: utf-8 -*-
"""
插件系统适配器

提供旧服务和新插件系统之间的转换层，确保平滑过渡。
"""

from typing import List, Dict, Any, Optional
import logging

from .plugins.manager import get_plugin_manager
from .plugins.base import (
    MarketDataSourcePlugin,
    CandleData,
    TickerData,
    PluginError,
)
from .services import MarketAPIError

logger = logging.getLogger(__name__)


class PluginAdapter:
    """插件适配器：将插件数据转换为旧格式"""
    
    @staticmethod
    def candle_to_dict(candle: CandleData) -> Dict[str, Any]:
        """将 CandleData 对象转换为字典"""
        return candle.to_dict()
    
    @staticmethod
    def candles_to_dict_list(candles: List[CandleData]) -> List[Dict[str, Any]]:
        """将 CandleData 列表转换为字典列表"""
        return [PluginAdapter.candle_to_dict(c) for c in candles]
    
    @staticmethod
    def ticker_to_dict(ticker: TickerData) -> Dict[str, Any]:
        """将 TickerData 对象转换为旧格式字典"""
        result = {
            'instId': ticker.inst_id,
            'last': str(ticker.last),
        }
        
        # 可选字段
        if ticker.bid is not None:
            result['bid'] = str(ticker.bid)
        if ticker.ask is not None:
            result['ask'] = str(ticker.ask)
        if ticker.high_24h is not None:
            result['high24h'] = str(ticker.high_24h)
        if ticker.low_24h is not None:
            result['low24h'] = str(ticker.low_24h)
        
        # 计算 open24h (如果有涨跌幅)
        if ticker.change_24h_pct is not None:
            open_24h = ticker.last / (1 + ticker.change_24h_pct / 100)
            result['open24h'] = str(open_24h)
        
        # 兼容旧字段名
        if 'high24h' in result:
            result['high_24h'] = result['high24h']
        if 'low24h' in result:
            result['low_24h'] = result['low24h']
        
        return result
    
    @staticmethod
    def plugin_error_to_api_error(error: PluginError) -> MarketAPIError:
        """将插件异常转换为旧的 API 异常"""
        return MarketAPIError(str(error))


class UnifiedMarketService:
    """
    统一的市场数据服务
    
    优先使用插件系统，失败时回退到旧服务（如果可用）
    """
    
    def __init__(self, source: str):
        """
        初始化服务
        
        Args:
            source: 数据源名称
        """
        self.source = source.lower()
        self._plugin_manager = get_plugin_manager()
        self._plugin = None
        self._use_plugin = True
        
        # 尝试获取插件
        try:
            self._plugin = self._plugin_manager.get_plugin(self.source)
            if self._plugin is None:
                logger.warning(f"插件 {self.source} 不存在，将尝试使用旧服务")
                self._use_plugin = False
        except Exception as e:
            logger.error(f"获取插件 {self.source} 失败: {e}")
            self._use_plugin = False
    
    def get_candlesticks(
        self,
        inst_id: str = "BTC-USDT",
        bar: str = "1H",
        limit: int = 100,
        before: int = None
    ) -> List[Dict[str, Any]]:
        """
        获取 K线数据
        
        Args:
            inst_id: 交易对
            bar: 时间周期
            limit: 返回数量
            before: 之前的时间戳（毫秒）
        
        Returns:
            K线数据字典列表
        
        Raises:
            MarketAPIError: 获取数据失败
        """
        if self._use_plugin and self._plugin:
            try:
                # 转换时间戳：旧接口用毫秒，插件用秒
                before_sec = before // 1000 if before else None
                
                # 调用插件
                candles = self._plugin.get_candlesticks(
                    symbol=inst_id,
                    bar=bar,
                    limit=limit,
                    before=before_sec
                )
                
                # 转换为字典格式
                result = PluginAdapter.candles_to_dict_list(candles)
                logger.debug(f"✅ 插件 {self.source} 返回 {len(result)} 条K线")
                return result
                
            except PluginError as e:
                logger.error(f"❌ 插件 {self.source} 获取K线失败: {e}")
                raise PluginAdapter.plugin_error_to_api_error(e)
            except Exception as e:
                logger.error(f"❌ 插件 {self.source} 意外错误: {e}")
                raise MarketAPIError(f"插件系统错误: {e}")
        else:
            # 回退到旧服务
            from .services import get_market_service
            logger.info(f"使用旧服务获取 {self.source} K线数据")
            service = get_market_service(self.source)
            return service.get_candlesticks(inst_id, bar, limit, before)
    
    def get_ticker(self, inst_id: str = "BTC-USDT") -> Dict[str, Any]:
        """
        获取最新行情
        
        Args:
            inst_id: 交易对
        
        Returns:
            行情数据字典
        
        Raises:
            MarketAPIError: 获取数据失败
        """
        if self._use_plugin and self._plugin:
            try:
                # 调用插件
                ticker = self._plugin.get_ticker(symbol=inst_id)
                
                # 转换为字典格式
                result = PluginAdapter.ticker_to_dict(ticker)
                logger.debug(f"✅ 插件 {self.source} 返回行情: {result.get('last')}")
                return result
                
            except PluginError as e:
                logger.error(f"❌ 插件 {self.source} 获取行情失败: {e}")
                raise PluginAdapter.plugin_error_to_api_error(e)
            except Exception as e:
                logger.error(f"❌ 插件 {self.source} 意外错误: {e}")
                raise MarketAPIError(f"插件系统错误: {e}")
        else:
            # 回退到旧服务
            from .services import get_market_service
            logger.info(f"使用旧服务获取 {self.source} 行情数据")
            service = get_market_service(self.source)
            return service.get_ticker(inst_id)
    
    @property
    def is_using_plugin(self) -> bool:
        """是否正在使用插件系统"""
        return self._use_plugin and self._plugin is not None


def get_unified_service(source: str) -> UnifiedMarketService:
    """
    获取统一的市场数据服务
    
    这是推荐的新接口，替代旧的 get_market_service()
    
    Args:
        source: 数据源名称
    
    Returns:
        UnifiedMarketService 实例
    
    Raises:
        MarketAPIError: 不支持的数据源
    """
    try:
        service = UnifiedMarketService(source)
        if not service.is_using_plugin:
            logger.warning(f"⚠️  数据源 {source} 使用旧服务实现")
        return service
    except Exception as e:
        raise MarketAPIError(f"初始化数据源 {source} 失败: {e}")
