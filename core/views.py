from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from .services import get_market_service, MarketAPIError, MARKET_SERVICES


def index(request):
    return HttpResponse('Hello, GeneticGrid!')


def market_view(request):
    """K 线看盘页面"""
    inst_id = request.GET.get('symbol', 'BTC-USDT')
    bar = request.GET.get('bar', '1H')
    source = request.GET.get('source', 'binance')
    return render(request, 'core/market.html', {
        'inst_id': inst_id,
        'bar': bar,
        'source': source,
        'sources': list(MARKET_SERVICES.keys()),
    })


def api_candlesticks(request):
    """K 线数据 API"""
    inst_id = request.GET.get('symbol', 'BTC-USDT')
    bar = request.GET.get('bar', '1H')
    limit = int(request.GET.get('limit', 100))
    source = request.GET.get('source', 'binance')

    try:
        service = get_market_service(source)
        candles = service.get_candlesticks(inst_id=inst_id, bar=bar, limit=limit)
        return JsonResponse({
            'code': 0,
            'data': candles,
            'symbol': inst_id,
            'bar': bar,
            'source': source,
        })
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
        return JsonResponse({
            'code': 0,
            'data': ticker,
            'source': source,
        })
    except MarketAPIError as e:
        return JsonResponse({
            'code': -1,
            'error': str(e),
            'source': source,
        }, status=500)
