from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from .services import get_market_service, MarketAPIError, MARKET_SERVICES
from .cache_service import CandlestickCacheService
from .proxy_config import is_proxy_available, get_proxy_url, get_okx_proxy, PROXY_CONFIG
import os
from pathlib import Path
import logging

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
    inst_id = request.GET.get('symbol', 'BTC-USDT')
    bar = request.GET.get('bar', '1H')
    limit = int(request.GET.get('limit', 100))
    source = request.GET.get('source', 'okx')
    before = request.GET.get('before')  # 获取该时间戳之前的数据（毫秒）
    after = request.GET.get('after')    # 获取该时间戳之后的数据（毫秒）
    
    # 转换时间戳：前端传的是毫秒，后端存储用秒
    before_sec = int(before) // 1000 if before else None
    after_sec = int(after) // 1000 if after else None

    try:
        # 使用缓存服务：优先从数据库读取，缺失时从API获取并缓存
        candles = CandlestickCacheService.get_with_auto_fetch(
            source=source,
            symbol=inst_id,
            bar=bar,
            limit=limit,
            before=before_sec,
            after=after_sec
        )
        
        # 获取缓存统计信息
        cache_info = CandlestickCacheService.get_cache_range(source, inst_id, bar)
        
        response = JsonResponse({
            'code': 0,
            'data': candles,
            'symbol': inst_id,
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
        logger.error(f"API error for {source}/{inst_id}/{bar}: {e}")
        return JsonResponse({
            'code': -1,
            'error': str(e),
            'symbol': inst_id,
            'bar': bar,
            'source': source,
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JsonResponse({
            'code': -1,
            'error': '服务器内部错误',
            'symbol': inst_id,
            'bar': bar,
            'source': source,
        }, status=500)


def api_ticker(request):
    """最新行情 API"""
    inst_id = request.GET.get('symbol', 'BTC-USDT')
    source = request.GET.get('source', 'okx')
    
    try:
        service = get_market_service(source)
        ticker = service.get_ticker(inst_id=inst_id)
        response = JsonResponse({
            'code': 0,
            'data': ticker,
            'source': source,
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
