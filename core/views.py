from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from .services import get_market_service, MarketAPIError, MARKET_SERVICES
import os
from pathlib import Path


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
    """K 线数据 API"""
    inst_id = request.GET.get('symbol', 'BTC-USDT')
    bar = request.GET.get('bar', '1H')
    limit = int(request.GET.get('limit', 100))
    source = request.GET.get('source', 'tradingview')
    before = request.GET.get('before')  # 获取该时间戳之前的数据
    after = request.GET.get('after')    # 获取该时间戳之后的数据
    
    if before:
        before = int(before)
    if after:
        after = int(after)

    try:
        service = get_market_service(source)
        
        # 如果有 after 参数，获取更新的数据
        if after:
            # 获取比指定时间更新的数据
            # 注意：这里简单实现，实际可能需要根据不同的API调整
            candles = service.get_candlesticks(inst_id=inst_id, bar=bar, limit=limit, before=None)
            # 过滤出时间戳大于 after 的数据
            candles = [c for c in candles if c['time'] > after // 1000]
        else:
            candles = service.get_candlesticks(inst_id=inst_id, bar=bar, limit=limit, before=before)
        
        response = JsonResponse({
            'code': 0,
            'data': candles,
            'symbol': inst_id,
            'bar': bar,
            'source': source,
        })
        # 设置缓存头，历史数据缓存更久
        if before or after:
            response['Cache-Control'] = 'public, max-age=300'  # 历史数据缓存5分钟
        else:
            response['Cache-Control'] = 'public, max-age=5'  # 最新数据缓存5秒
        return response
    except MarketAPIError as e:
        return JsonResponse({
            'code': -1,
            'error': str(e),
            'symbol': inst_id,
            'bar': bar,
            'source': source,
        }, status=500)


def api_ticker(request):
    """最新行情 API"""
    inst_id = request.GET.get('symbol', 'BTC-USDT')
    source = request.GET.get('source', 'binance')
    
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
