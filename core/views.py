from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from .services import MarketAPIError
from .plugin_adapter import get_unified_service
from .cache_service import CandlestickCacheService
from .derivative_cache import DerivativeDataCacheService
from .proxy_config import is_proxy_available, get_proxy_url, get_proxy, PROXY_CONFIG
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
    mode = request.GET.get('mode', 'spot').lower()
    before = request.GET.get('before')  # 毫秒时间戳
    after = request.GET.get('after')    # 毫秒时间戳

    if mode not in {'spot', 'contract'}:
        return JsonResponse({
            'code': -1,
            'error': f"不支持的交易模式: {mode}",
            'symbol': symbol,
            'bar': bar,
            'source': source,
        }, status=400)
    
    # 转换时间戳：前端传毫秒，插件需要秒
    before_sec = int(before) // 1000 if before else None
    after_sec = int(after) // 1000 if after else None
    
    logger.info(f"📊 K线请求: {symbol}, {bar}, {source}, mode={mode}")

    try:
        # 插件会自动处理格式转换（BTCUSDT -> BTC-USDT, 1h -> 1H）
        candles = CandlestickCacheService.get_with_auto_fetch(
            source=source,
            symbol=symbol,  # 标准格式
            bar=bar,        # 标准格式
            mode=mode,
            limit=limit,
            before=before_sec,
            after=after_sec
        )
        
        # 获取缓存统计信息
        cache_info = CandlestickCacheService.get_cache_range(source, symbol, bar, mode)
        
        response = JsonResponse({
            'code': 0,
            'data': candles,
            'symbol': symbol,
            'bar': bar,
            'source': source,
            'mode': mode,
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
            'mode': mode,
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JsonResponse({
            'code': -1,
            'error': '服务器内部错误',
            'symbol': symbol,
            'bar': bar,
            'source': source,
            'mode': mode,
        }, status=500)


def api_ticker(request):
    """最新行情 API"""
    # 前端使用标准格式
    symbol = request.GET.get('symbol', 'BTCUSDT')
    source = request.GET.get('source', 'okx')
    mode = request.GET.get('mode', 'spot').lower()
    
    if mode not in {'spot', 'contract'}:
        return JsonResponse({
            'code': -1,
            'error': f"不支持的交易模式: {mode}",
            'source': source,
        }, status=400)

    logger.info(f"📈 行情请求: {symbol} ({source}) mode={mode}")
    
    try:
        # 插件会自动处理格式转换（BTCUSDT -> BTC-USDT）
        service = get_unified_service(source)
        ticker = service.get_ticker(inst_id=symbol, mode=mode)
        
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
            'mode': mode,
            'using_plugin': service.is_using_plugin,
        })
        response['Cache-Control'] = 'public, max-age=3'  # 行情缓存3秒
        return response
    except MarketAPIError as e:
        return JsonResponse({
            'code': -1,
            'error': str(e),
            'source': source,
            'mode': mode,
        }, status=500)


def api_funding_rate(request):
    """资金费率 API - 仅合约模式"""
    symbol = request.GET.get('symbol', 'BTCUSDT')
    source = request.GET.get('source', 'okx')
    
    logger.info(f"💰 资金费率请求: {symbol} ({source})")
    
    # 尝试从缓存获取
    cached_data = DerivativeDataCacheService.get_funding_rate_from_cache(source, symbol)
    if cached_data:
        logger.info(f"✅ 资金费率缓存命中: {symbol}")
        response = JsonResponse({
            'code': 0,
            'data': cached_data,
            'symbol': symbol,
            'source': source,
            'cached': True
        })
        response['Cache-Control'] = 'public, max-age=30'
        return response
    
    try:
        plugin_manager = get_plugin_manager()
        plugin = plugin_manager.get_plugin(source)
        
        if not plugin:
            return JsonResponse({
                'code': -1,
                'error': f'数据源 {source} 不可用'
            }, status=404)
        
        capability = plugin.get_capability()
        if not capability.supports_funding_rate:
            return JsonResponse({
                'code': -1,
                'error': f'数据源 {source} 不支持资金费率查询'
            }, status=400)
        
        funding_data = plugin.get_funding_rate(symbol=symbol)
        data_dict = funding_data.to_dict()
        
        # 保存到缓存
        DerivativeDataCacheService.save_funding_rate_to_cache(source, symbol, data_dict)
        
        response = JsonResponse({
            'code': 0,
            'data': data_dict,
            'symbol': symbol,
            'source': source,
            'cached': False
        })
        response['Cache-Control'] = 'public, max-age=30'
        return response
        
    except PluginError as e:
        logger.error(f"Plugin error: {e}")
        return JsonResponse({
            'code': -1,
            'error': str(e),
            'source': source,
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JsonResponse({
            'code': -1,
            'error': '服务器内部错误',
            'source': source,
        }, status=500)


def api_funding_rate_history(request):
    """资金费率历史数据 API"""
    symbol = request.GET.get('symbol', 'BTCUSDT')
    source = request.GET.get('source', 'okx')
    limit = int(request.GET.get('limit', '100'))
    granularity = request.GET.get('granularity', '8h')  # 资金费率默认8小时
    
    logger.info(f"📈 资金费率历史请求: {symbol} ({source}) limit={limit} granularity={granularity}")
    
    # 尝试从缓存获取
    cached_history = DerivativeDataCacheService.get_funding_history_from_cache(source, symbol)
    if cached_history and len(cached_history) >= limit:
        logger.info(f"✅ 资金费率历史缓存命中: {symbol}, {len(cached_history)}条")
        # 返回最近的limit条
        response = JsonResponse({
            'code': 0,
            'data': cached_history[-limit:],
            'symbol': symbol,
            'source': source,
            'cached': True
        })
        response['Cache-Control'] = 'public, max-age=300'
        return response
    
    try:
        plugin_manager = get_plugin_manager()
        plugin = plugin_manager.get_plugin(source)
        
        if not plugin:
            return JsonResponse({
                'code': -1,
                'error': f'数据源 {source} 不可用'
            }, status=404)
        
        capability = plugin.get_capability()
        if not capability.supports_funding_rate:
            return JsonResponse({
                'code': -1,
                'error': f'数据源 {source} 不支持资金费率查询'
            }, status=400)
        
        # 调用插件的历史数据方法
        history_data = plugin.get_funding_rate_history(symbol=symbol, limit=limit)
        
        # 保存到缓存
        if history_data:
            DerivativeDataCacheService.save_funding_history_to_cache(source, symbol, history_data)
        
        response = JsonResponse({
            'code': 0,
            'data': history_data,
            'symbol': symbol,
            'source': source,
            'cached': False
        })
        response['Cache-Control'] = 'public, max-age=300'  # 缓存5分钟
        return response
        
    except PluginError as e:
        logger.error(f"Plugin error: {e}")
        return JsonResponse({
            'code': -1,
            'error': str(e),
            'source': source,
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JsonResponse({
            'code': -1,
            'error': '服务器内部错误',
            'source': source,
        }, status=500)


def api_contract_basis_history(request):
    """合约基差历史数据 API"""
    symbol = request.GET.get('symbol', 'BTCUSDT')
    source = request.GET.get('source', 'okx')
    contract_type = request.GET.get('contract_type', 'perpetual')
    limit = int(request.GET.get('limit', '720'))
    granularity = request.GET.get('granularity', '1h')  # 默认1小时
    
    logger.info(f"📈 合约基差历史请求: {symbol} ({source}) type={contract_type} limit={limit} granularity={granularity}")
    
    # 尝试从缓存获取（包含granularity的缓存key）
    cache_key = f"{source}:{symbol}:{contract_type}:{granularity}"
    cached_history = DerivativeDataCacheService.get_basis_history_from_cache(source, symbol, contract_type, granularity)
    if cached_history and len(cached_history) >= limit:
        logger.info(f"✅ 合约基差历史缓存命中: {symbol} ({granularity}), {len(cached_history)}条")
        response = JsonResponse({
            'code': 0,
            'data': cached_history[-limit:],  # 返回最近的limit条
            'symbol': symbol,
            'source': source,
            'granularity': granularity,
            'cached': True
        })
        response['Cache-Control'] = 'public, max-age=300'
        return response
    
    try:
        plugin_manager = get_plugin_manager()
        plugin = plugin_manager.get_plugin(source)
        
        if not plugin:
            return JsonResponse({
                'code': -1,
                'error': f'数据源 {source} 不可用'
            }, status=404)
        
        capability = plugin.get_capability()
        if not capability.supports_contract_basis:
            return JsonResponse({
                'code': -1,
                'error': f'数据源 {source} 不支持合约基差查询'
            }, status=400)
        
        # 调用插件的历史数据方法
        history_data = plugin.get_contract_basis_history(
            symbol=symbol,
            contract_type=contract_type,
            limit=limit,
            granularity=granularity
        )
        
        # 保存到缓存（包含granularity）
        if history_data:
            DerivativeDataCacheService.save_basis_history_to_cache(source, symbol, contract_type, history_data, granularity)
        
        response = JsonResponse({
            'code': 0,
            'data': history_data,
            'symbol': symbol,
            'source': source,
            'cached': False
        })
        response['Cache-Control'] = 'public, max-age=300'  # 缓存5分钟
        return response
        
    except PluginError as e:
        logger.error(f"Plugin error: {e}")
        return JsonResponse({
            'code': -1,
            'error': str(e),
            'source': source,
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JsonResponse({
            'code': -1,
            'error': '服务器内部错误',
            'source': source,
        }, status=500)


def api_contract_basis(request):
    """合约基差 API - 仅合约模式"""
    symbol = request.GET.get('symbol', 'BTCUSDT')
    source = request.GET.get('source', 'okx')
    contract_type = request.GET.get('contract_type', 'perpetual')
    
    logger.info(f"📊 合约基差请求: {symbol} ({source}) type={contract_type}")
    
    # 尝试从缓存获取
    cached_data = DerivativeDataCacheService.get_basis_from_cache(source, symbol, contract_type)
    if cached_data:
        logger.info(f"✅ 合约基差缓存命中: {symbol}")
        response = JsonResponse({
            'code': 0,
            'data': cached_data,
            'symbol': symbol,
            'source': source,
            'cached': True
        })
        response['Cache-Control'] = 'public, max-age=30'
        return response
    
    try:
        plugin_manager = get_plugin_manager()
        plugin = plugin_manager.get_plugin(source)
        
        if not plugin:
            return JsonResponse({
                'code': -1,
                'error': f'数据源 {source} 不可用'
            }, status=404)
        
        capability = plugin.get_capability()
        if not capability.supports_contract_basis:
            return JsonResponse({
                'code': -1,
                'error': f'数据源 {source} 不支持合约基差查询'
            }, status=400)
        
        basis_data = plugin.get_contract_basis(
            symbol=symbol,
            contract_type=contract_type
        )
        data_dict = basis_data.to_dict()
        
        # 保存到缓存
        DerivativeDataCacheService.save_basis_to_cache(source, symbol, contract_type, data_dict)
        
        response = JsonResponse({
            'code': 0,
            'data': data_dict,
            'symbol': symbol,
            'source': source,
            'cached': False
        })
        response['Cache-Control'] = 'public, max-age=30'
        return response
        
    except PluginError as e:
        logger.error(f"Plugin error: {e}")
        return JsonResponse({
            'code': -1,
            'error': str(e),
            'source': source,
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JsonResponse({
            'code': -1,
            'error': '服务器内部错误',
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
            'proxy': get_proxy(),
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
