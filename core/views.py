from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from .services import MarketAPIError
from .plugin_adapter import get_unified_service
from .cache_service import CandlestickCacheService
from .proxy_config import is_proxy_available, get_proxy_url, get_okx_proxy, PROXY_CONFIG
from .plugins.manager import get_plugin_manager
from .plugins.documentation import DocumentationGenerator
from .plugins.base import PluginError
from .protocol import ProtocolConverter
import os
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)


def index(request):
    """主页 - 返回 Vue 应用"""
    # 返回 Vue 构建的 index.html
    static_dir = Path(__file__).resolve().parent.parent / 'static' / 'dist'
    index_path = static_dir / 'index.html'
    
    with open(index_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return HttpResponse(html_content)


def market_view(request):
    """K 线看盘页面 - 返回 Vue 应用"""
    # Vue 应用会通过路由处理所有页面
    return index(request)


def api_candlesticks(request):
    """K 线数据 API - 使用数据库缓存"""
    # 前端使用标准格式（如 BTCUSDT, 1h）
    symbol = request.GET.get('symbol', 'BTCUSDT')
    bar = request.GET.get('bar', '1h')
    limit = int(request.GET.get('limit', 100))
    source = request.GET.get('source', 'okx')
    before = request.GET.get('before')  # 毫秒时间戳
    after = request.GET.get('after')    # 毫秒时间戳
    
    # 转换时间戳：前端传毫秒，插件需要秒
    before_sec = int(before) // 1000 if before else None
    after_sec = int(after) // 1000 if after else None
    
    logger.info(f"📊 K线请求: {symbol}, {bar}, {source}")

    try:
        # 插件会自动处理格式转换（BTCUSDT -> BTC-USDT, 1h -> 1H）
        candles = CandlestickCacheService.get_with_auto_fetch(
            source=source,
            symbol=symbol,  # 标准格式
            bar=bar,        # 标准格式
            limit=limit,
            before=before_sec,
            after=after_sec
        )
        
        # 获取缓存统计信息
        cache_info = CandlestickCacheService.get_cache_range(source, symbol, bar)
        
        response = JsonResponse({
            'code': 0,
            'data': candles,
            'symbol': symbol,
            'bar': bar,
            'source': source,
            'cache_info': {
                'count': cache_info['count'],
                'oldest': cache_info['oldest'],
                'newest': cache_info['newest'],
            }
        })
        
        # 设置缓存头
        if before or after:
            response['Cache-Control'] = 'public, max-age=300'  # 历史数据缓存5分钟
        else:
            response['Cache-Control'] = 'public, max-age=5'  # 最新数据缓存5秒
        
        return response
        
    except MarketAPIError as e:
        logger.error(f"API error for {source}/{symbol}/{bar}: {e}")
        return JsonResponse({
            'code': -1,
            'error': str(e),
            'symbol': symbol,
            'bar': bar,
            'source': source,
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JsonResponse({
            'code': -1,
            'error': '服务器内部错误',
            'symbol': symbol,
            'bar': bar,
            'source': source,
        }, status=500)


def api_ticker(request):
    """最新行情 API"""
    # 前端使用标准格式
    symbol = request.GET.get('symbol', 'BTCUSDT')
    source = request.GET.get('source', 'okx')
    
    logger.info(f"📈 行情请求: {symbol} ({source})")
    
    try:
        # 插件会自动处理格式转换（BTCUSDT -> BTC-USDT）
        service = get_unified_service(source)
        ticker = service.get_ticker(inst_id=symbol)
        
        # 日志标记数据来源
        if service.is_using_plugin:
            logger.debug(f"📦 使用插件获取行情 {source}/{symbol}")
        else:
            logger.debug(f"🔧 使用旧服务获取行情 {source}/{symbol}")
        
        response = JsonResponse({
            'code': 0,
            'data': ticker,
            'symbol': symbol,
            'source': source,
            'using_plugin': service.is_using_plugin,
        })
        response['Cache-Control'] = 'public, max-age=3'  # 行情缓存3秒
        return response
    except MarketAPIError as e:
        return JsonResponse({
            'code': -1,
            'error': str(e),
            'source': source,
        }, status=500)


def api_proxy_status(request):
    """代理状态 API"""
    try:
        socks5_config = PROXY_CONFIG['socks5']
        http_config = PROXY_CONFIG['http']
        
        status = {
            'proxy_enabled': True,
            'socks5': {
                'host': socks5_config['host'],
                'port': socks5_config['port'],
                'available': is_proxy_available('socks5'),
                'url': get_proxy_url('socks5'),
            },
            'http': {
                'host': http_config['host'],
                'port': http_config['port'],
                'available': is_proxy_available('http'),
                'url': get_proxy_url('http'),
            },
            'okx_proxy': get_okx_proxy(),
        }
        
        return JsonResponse({
            'code': 0,
            'data': status,
        })
    except Exception as e:
        logger.error(f"获取代理状态失败: {e}")
        return JsonResponse({
            'code': -1,
            'error': str(e),
        }, status=500)


def api_sources(request):
    """数据源列表 API - 返回所有已注册的数据源及其能力"""
    try:
        manager = get_plugin_manager()
        sources = {}
        
        for name, plugin in manager.get_all_plugins().items():
            metadata = plugin.get_metadata()
            capability = plugin.get_capability()
            
            sources[name] = {
                'metadata': metadata.to_dict(),
                'capability': capability.to_dict(),
            }
        
        return JsonResponse({
            'code': 0,
            'data': sources,
            'total': len(sources),
        })
    except Exception as e:
        logger.error(f"获取数据源列表失败: {e}")
        return JsonResponse({
            'code': -1,
            'error': str(e),
        }, status=500)


def api_source_capabilities(request, source_name):
    """获取指定数据源的详细能力 API"""
    try:
        manager = get_plugin_manager()
        plugin = manager.get_plugin(source_name)
        
        if not plugin:
            return JsonResponse({
                'code': -1,
                'error': f'数据源 "{source_name}" 不存在',
            }, status=404)
        
        metadata = plugin.get_metadata()
        capability = plugin.get_capability()
        
        return JsonResponse({
            'code': 0,
            'data': {
                'name': source_name,
                'metadata': metadata.to_dict(),
                'capability': capability.to_dict(),
                'documentation': DocumentationGenerator.generate_plugin_doc(plugin),
            }
        })
    except Exception as e:
        logger.error(f"获取数据源能力失败: {e}")
        return JsonResponse({
            'code': -1,
            'error': str(e),
        }, status=500)


def api_source_documentation(request):
    """获取所有数据源的文档 API"""
    try:
        manager = get_plugin_manager()
        doc = DocumentationGenerator.generate_all_plugins_doc(manager)
        
        return JsonResponse({
            'code': 0,
            'data': {
                'markdown': doc,
                'json': DocumentationGenerator.generate_capabilities_json(manager),
            }
        })
    except Exception as e:
        logger.error(f"生成文档失败: {e}")
        return JsonResponse({
            'code': -1,
            'error': str(e),
        }, status=500)
