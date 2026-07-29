from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.timezone import now
from .services import MarketAPIError
from .plugin_adapter import get_unified_service
from .cache_service import CandlestickCacheService
from .derivative_cache import DerivativeDataCacheService
from .proxy_config import (
    get_proxy_settings_snapshot,
    update_proxy_settings,
    clear_proxy_cache,
    is_proxy_available,
    test_proxy_url,
    get_proxy_dict,
)
from .plugins.manager import get_plugin_manager
from .plugins.documentation import DocumentationGenerator
from .plugins.base import PluginError
from .protocol import ProtocolConverter
from .okx_auth import (
    encrypt_credential, decrypt_credential,
    hash_passphrase, verify_passphrase,
    fetch_account_info, fetch_balance, fetch_positions,
    post_order, cancel_order, has_trade_permission,
    okx_api_request,
    OKX_DEMO_URL, OKX_REAL_URL,
)
from .models import OKXAccount
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
    
    # Redis 未命中，尝试从数据库获取
    db_history = DerivativeDataCacheService.get_funding_history_from_db(source, symbol, limit, granularity)
    if db_history:
        logger.info(f"📦 资金费率历史数据库命中: {symbol}, {len(db_history)}条")
        # 回填 Redis 缓存
        DerivativeDataCacheService.save_funding_history_to_cache(source, symbol, db_history)
        response = JsonResponse({
            'code': 0,
            'data': db_history[-limit:],
            'symbol': symbol,
            'source': source,
            'cached': True,
            'source_cache': 'db',
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
            # 持久化到数据库
            DerivativeDataCacheService.save_funding_history_to_db(source, symbol, history_data, granularity)
        
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
    
    # Redis 未命中，尝试从数据库获取
    db_history = DerivativeDataCacheService.get_basis_history_from_db(source, symbol, contract_type, limit, granularity)
    if db_history:
        logger.info(f"📦 基差历史数据库命中: {symbol} ({granularity}), {len(db_history)}条")
        # 回填 Redis 缓存
        DerivativeDataCacheService.save_basis_history_to_cache(source, symbol, contract_type, db_history, granularity)
        response = JsonResponse({
            'code': 0,
            'data': db_history[-limit:],
            'symbol': symbol,
            'source': source,
            'granularity': granularity,
            'cached': True,
            'source_cache': 'db',
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
            # 持久化到数据库
            DerivativeDataCacheService.save_basis_history_to_db(source, symbol, contract_type, history_data, granularity)
        
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
        return JsonResponse({
            'code': 0,
            'data': get_proxy_settings_snapshot(),
        })
    except Exception as e:
        logger.error(f"获取代理状态失败: {e}")
        return JsonResponse({
            'code': -1,
            'error': str(e),
        }, status=500)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def api_proxy_config(request):
    """代理配置 API（GET 查询，POST 更新）。"""
    try:
        if request.method == 'GET':
            return JsonResponse({
                'code': 0,
                'data': get_proxy_settings_snapshot(),
            })

        payload = json.loads(request.body.decode('utf-8') or '{}')
        updated = update_proxy_settings(payload)
        return JsonResponse({
            'code': 0,
            'data': updated,
            'message': '代理配置已更新并持久化',
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'code': -1,
            'error': '请求体必须为合法 JSON',
        }, status=400)
    except ValueError as e:
        return JsonResponse({
            'code': -1,
            'error': str(e),
        }, status=400)
    except Exception as e:
        logger.error(f"代理配置更新失败: {e}")
        return JsonResponse({
            'code': -1,
            'error': str(e),
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_proxy_test(request):
    """测试代理连通性。

    支持请求体传入 proxy_url，仅测试该地址；
    未传入时兼容旧行为（同时返回 http/socks5 状态）。
    """
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
        proxy_url = payload.get('proxy_url') if isinstance(payload, dict) else None

        if isinstance(proxy_url, str) and proxy_url.strip():
            result = test_proxy_url(proxy_url.strip())
            return JsonResponse({
                'code': 0,
                'data': result,
            })

        clear_proxy_cache()
        http_ok = is_proxy_available('http')
        socks5_ok = is_proxy_available('socks5')
        return JsonResponse({
            'code': 0,
            'data': {
                'available': http_ok or socks5_ok,
                'http': http_ok,
                'socks5': socks5_ok,
            }
        })
    except Exception as e:
        logger.error(f"代理测试失败: {e}")
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


def api_symbols(request):
    """按市值排序的交易对列表（用于前端符号选择器）
    
    优先使用 CoinGecko 的市值数据排序，按市值降序返回。
    如果没有 CoinGecko 数据，回退到 OKX 插件支持的符号列表。
    """
    source = request.GET.get('source', 'coingecko')
    limit = int(request.GET.get('limit', '100'))
    
    try:
        plugin_manager = get_plugin_manager()
        plugin = plugin_manager.get_plugin(source)
        
        if not plugin:
            # 回退：使用 OKX 支持的符号
            fallback = plugin_manager.get_plugin('okx')
            symbols = fallback.get_capability().supported_symbols if fallback else [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
                "DOGEUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT", "BNBUSDT",
            ]
            data = [{"inst_id": s, "last": None, "market_cap": None,
                     "market_cap_rank": None, "change_24h_pct": None, "volume_24h": None}
                    for s in symbols[:limit]]
            return JsonResponse({"code": 0, "data": data})
        
        # 检查插件是否有 get_tickers 方法
        get_tickers = getattr(plugin, 'get_tickers', None)
        if callable(get_tickers):
            try:
                tickers = get_tickers(mode='spot', limit=limit)
                if tickers:
                    return JsonResponse({"code": 0, "data": tickers})
            except Exception as ticker_err:
                logger.warning(f"CoinGecko tickers 失败, 回退到 OKX: {ticker_err}")
                # 回退到 OKX 的 supported_symbols
        
        # 回退：使用 OKX 支持的符号
        fallback = plugin_manager.get_plugin('okx')
        symbols = fallback.get_capability().supported_symbols if fallback else [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
            "DOGEUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT", "BNBUSDT",
        ]
        data = [{"inst_id": s, "last": None, "market_cap": None,
                 "market_cap_rank": None, "change_24h_pct": None, "volume_24h": None}
                for s in symbols[:limit]]
        return JsonResponse({"code": 0, "data": data})
            
    except Exception as e:
        logger.error(f"获取符号列表失败: {e}")
        return JsonResponse({"code": -1, "error": str(e)}, status=500)


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


# ──────────────────────────────────────────────
# OKX 账户认证系统
# ──────────────────────────────────────────────

def _session_creds(request) -> tuple:
    """从 session 取明文凭证，未登陆则抛出异常"""
    creds = request.session.get('okx_credentials')
    if not creds:
        raise Exception('未登录')
    return creds['api_key'], creds['secret_key'], creds['passphrase'], creds.get('is_demo', False)


@csrf_exempt
def api_account_register(request):
    """注册 API Key"""
    if request.method != 'POST':
        return JsonResponse({'code': -1, 'error': '仅支持 POST'}, status=405)
    try:
        data = json.loads(request.body)
        label = data.get('label', '').strip()
        api_key = data.get('api_key', '').strip()
        secret_key = data.get('secret_key', '').strip()
        passphrase = data.get('passphrase', '').strip()
        note = data.get('note', '').strip()
        is_demo = data.get('is_demo', False)

        if not all([label, api_key, secret_key, passphrase]):
            return JsonResponse({'code': -1, 'error': '缺少必填字段'}, status=400)

        if OKXAccount.objects.filter(api_key=api_key).exists():
            return JsonResponse({'code': -1, 'error': '该 API Key 已注册'}, status=409)

        # 测试连通性（模拟盘需加 x-simulated-trading: 1 头）
        info = fetch_account_info(api_key, secret_key, passphrase, is_demo=is_demo)

        account = OKXAccount.objects.create(
            label=label,
            api_key=api_key,
            encrypted_secret_key=encrypt_credential(secret_key),
            encrypted_passphrase=encrypt_credential(passphrase),
            passphrase_hash=hash_passphrase(passphrase),
            account_info=info,
            note=note,
            is_demo=is_demo,
        )

        # 注册成功后自动登陆
        request.session['okx_credentials'] = {
            'api_key': account.api_key,
            'secret_key': secret_key,
            'passphrase': passphrase,
            'account_id': account.pk,
            'label': account.label,
            'is_demo': is_demo,
            'trade_permission': has_trade_permission(account.account_info or {}),
        }
        request.session.set_expiry(0)

        return JsonResponse({
            'code': 0,
            'data': {
                'id': account.pk,
                'label': account.label,
                'api_key_masked': account.api_key[:8] + '****',
                'note': account.note,
                'is_demo': is_demo,
                'account_info': info,
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'code': -1, 'error': '请求格式错误'}, status=400)
    except Exception as e:
        logger.error(f"注册失败: {e}")
        return JsonResponse({'code': -1, 'error': str(e)}, status=400)


def api_account_list(request):
    """列出已注册的 API Key"""
    accounts = OKXAccount.objects.filter(is_active=True).order_by('-created_at')
    data = []
    for a in accounts:
        data.append({
            'id': a.pk,
            'label': a.label,
            'api_key_masked': a.api_key[:8] + '****',
            'note': a.note,
            'is_demo': a.is_demo,
            'account_info': a.account_info,
            'last_used_at': a.last_used_at.isoformat() if a.last_used_at else None,
            'created_at': a.created_at.isoformat(),
        })
    return JsonResponse({'code': 0, 'data': data})


@csrf_exempt
def api_account_login(request):
    """用 passphrase 登陆"""
    if request.method != 'POST':
        return JsonResponse({'code': -1, 'error': '仅支持 POST'}, status=405)
    try:
        data = json.loads(request.body)
        account_id = data.get('account_id')
        passphrase_input = data.get('passphrase', '').strip()

        if not account_id or not passphrase_input:
            return JsonResponse({'code': -1, 'error': '缺少参数'}, status=400)

        try:
            account = OKXAccount.objects.get(pk=account_id, is_active=True)
        except OKXAccount.DoesNotExist:
            return JsonResponse({'code': -1, 'error': '账户不存在'}, status=404)

        if not verify_passphrase(passphrase_input, account.passphrase_hash):
            return JsonResponse({'code': -1, 'error': 'passphrase 错误'}, status=403)

        secret_key = decrypt_credential(bytes(account.encrypted_secret_key))
        enc_pass = decrypt_credential(bytes(account.encrypted_passphrase))

        # 重新获取账户信息（刷新 perm 等字段）
        base_url = OKX_DEMO_URL if account.is_demo else OKX_REAL_URL
        try:
            fresh_info = fetch_account_info(account.api_key, secret_key, enc_pass, base_url=base_url, is_demo=account.is_demo)
            account.account_info = fresh_info
            account.save(update_fields=['account_info'])
        except Exception:
            pass

        # 存入 session
        request.session['okx_credentials'] = {
            'api_key': account.api_key,
            'secret_key': secret_key,
            'passphrase': enc_pass,
            'account_id': account.pk,
            'label': account.label,
            'is_demo': account.is_demo,
            'trade_permission': has_trade_permission(account.account_info or {}),
        }
        request.session.set_expiry(0)  # 浏览器会话级

        account.last_used_at = now()
        account.save(update_fields=['last_used_at'])

        return JsonResponse({
            'code': 0,
            'data': {
                'id': account.pk,
                'label': account.label,
                'api_key_masked': account.api_key[:8] + '****',
                'note': account.note,
                'is_demo': account.is_demo,
                'account_info': account.account_info,
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'code': -1, 'error': '请求格式错误'}, status=400)
    except Exception as e:
        logger.error(f"登陆失败: {e}")
        return JsonResponse({'code': -1, 'error': str(e)}, status=400)


@csrf_exempt
def api_account_refresh(request):
    """重新拉取 OKX 账户信息，刷新 session 中的权限"""
    try:
        api_key, secret_key, passphrase, is_demo = _session_creds(request)
        creds = request.session.get('okx_credentials', {})
        account_id = creds.get('account_id')
        if not account_id:
            return JsonResponse({'code': -1, 'error': '未登录'}, status=401)

        base_url = OKX_DEMO_URL if is_demo else OKX_REAL_URL
        fresh_info = fetch_account_info(api_key, secret_key, passphrase, base_url=base_url, is_demo=is_demo)

        # 更新 DB
        try:
            account = OKXAccount.objects.get(pk=account_id)
            account.account_info = fresh_info
            account.save(update_fields=['account_info'])
        except OKXAccount.DoesNotExist:
            pass

        # 更新 session
        creds['trade_permission'] = has_trade_permission(fresh_info)
        request.session['okx_credentials'] = creds

        return JsonResponse({
            'code': 0,
            'data': {
                'trade_permission': has_trade_permission(fresh_info),
                'account_info': fresh_info,
            }
        })
    except Exception as e:
        logger.error(f"刷新账户信息失败: {e}")
        return JsonResponse({'code': -1, 'error': str(e)}, status=400)


@csrf_exempt
def api_account_logout(request):
    """登出"""
    request.session.pop('okx_credentials', None)
    return JsonResponse({'code': 0, 'data': {'ok': True}})


def api_account_session(request):
    """检查当前 session 状态（自动刷新权限）"""
    creds = request.session.get('okx_credentials')
    if creds:
        # 自动从 OKX 拉取最新账户信息，刷新权限
        try:
            fresh_info = fetch_account_info(
                creds['api_key'], creds['secret_key'], creds['passphrase'],
                is_demo=creds.get('is_demo', False),
            )
            creds['trade_permission'] = has_trade_permission(fresh_info)
            request.session['okx_credentials'] = creds
            # 更新 DB
            account_id = creds.get('account_id')
            if account_id:
                try:
                    account = OKXAccount.objects.get(pk=account_id)
                    account.account_info = fresh_info
                    account.save(update_fields=['account_info'])
                except OKXAccount.DoesNotExist:
                    pass
        except Exception:
            pass

        return JsonResponse({
            'code': 0,
            'data': {
                'authenticated': True,
                'account_id': creds['account_id'],
                'label': creds['label'],
                'api_key_masked': creds['api_key'][:8] + '****',
                'trade_permission': creds.get('trade_permission', False),
            }
        })
    return JsonResponse({
        'code': 0,
        'data': {'authenticated': False}
    })


def api_account_balance(request):
    """获取账户余额（需 session）"""
    try:
        api_key, secret_key, passphrase, is_demo = _session_creds(request)
        balance = fetch_balance(api_key, secret_key, passphrase, is_demo=is_demo)
        return JsonResponse({'code': 0, 'data': balance})
    except Exception as e:
        return JsonResponse({'code': -1, 'error': str(e)}, status=401 if '未登录' in str(e) else 400)


def api_account_positions(request):
    """获取持仓（需 session），包含合约持仓 + 现货余额"""
    try:
        api_key, secret_key, passphrase, is_demo = _session_creds(request)
        positions = fetch_positions(api_key, secret_key, passphrase, is_demo=is_demo)
        balance = fetch_balance(api_key, secret_key, passphrase, is_demo=is_demo)
        spot_holdings = []
        for d in balance.get('details', []):
            eq = float(d.get('eq', '0'))
            eq_usd = float(d.get('eqUsd', '0'))
            if eq <= 0:
                continue
            open_avg_px = d.get('openAvgPx')
            spot_upl = d.get('spotUpl')
            spot_upl_ratio = d.get('spotUplRatio')
            spot_holdings.append({
                'symbol': d.get('ccy', ''),
                'positionQty': eq,
                'notionalValue': eq_usd,
                'markPrice': eq_usd / eq if eq > 0 else 0,
                'leverage': 1,
                'mgnMode': 'spot',
                'side': 'spot',
                'available': float(d.get('availBal', '0')),
                'frozenQty': float(d.get('frozenBal', '0')),
                'unrealizedPnl': float(spot_upl) if spot_upl else 0,
                'unrealizedPnlRatio': float(spot_upl_ratio) if spot_upl_ratio else 0,
                'avgCostPrice': float(open_avg_px) if open_avg_px else None,
                'timestamp': '',
            })
        return JsonResponse({
            'code': 0,
            'data': {
                'source': 'okx',
                'positions': positions + spot_holdings,
                'total': len(positions) + len(spot_holdings),
            }
        })
    except Exception as e:
        return JsonResponse({'code': -1, 'error': str(e)}, status=401 if '未登录' in str(e) else 400)


@csrf_exempt
def api_account_delete(request, account_id):
    """删除当前登录的 API Key"""
    if request.method != 'DELETE':
        return JsonResponse({'code': -1, 'error': '仅支持 DELETE'}, status=405)
    creds = request.session.get('okx_credentials')
    if not creds:
        return JsonResponse({'code': -1, 'error': '未登录'}, status=401)
    if creds.get('account_id') != account_id:
        return JsonResponse({'code': -1, 'error': '只能删除自己当前登录的账户'}, status=403)
    try:
        account = OKXAccount.objects.get(pk=account_id)
        account.delete()
        request.session.pop('okx_credentials', None)
        return JsonResponse({'code': 0, 'data': {'ok': True}})
    except OKXAccount.DoesNotExist:
        return JsonResponse({'code': -1, 'error': '账户不存在'}, status=404)


# ──────────────────────────────────────────────
# 交易对列表（从 OKX 实时拉取）
# ──────────────────────────────────────────────

def api_account_symbols(request):
    """获取 OKX 交易对列表"""
    inst_type = request.GET.get('type', 'SPOT').upper()
    try:
        import requests
        url = 'https://www.okx.com/api/v5/public/instruments'
        resp = requests.get(url, params={'instType': inst_type}, proxies=get_proxy_dict(), timeout=15)
        result = resp.json()
        if result.get('code') != '0':
            return JsonResponse({'code': 0, 'data': []})

        symbols = []
        for item in result.get('data', []):
            inst_id = item.get('instId', '')
            if inst_type == 'SWAP':
                if inst_id.endswith('USDT-SWAP') or inst_id.endswith('USD-SWAP'):
                    # BTC-USDT-SWAP → BTCUSDT
                    parts = inst_id.split('-')
                    symbols.append(parts[0] + parts[1])
            else:
                base, _, quote = inst_id.partition('-')
                if quote == 'USDT':
                    symbols.append(base + quote)
        symbols.sort()
        return JsonResponse({'code': 0, 'data': symbols})
    except Exception as e:
        logger.warning(f"获取交易对列表失败: {e}")
        return JsonResponse({'code': 0, 'data': []})


# ──────────────────────────────────────────────
# 期权数据（从 OKX 实时拉取）
# ──────────────────────────────────────────────


def api_option_instruments(request):
    """获取 OKX 期权合约列表"""
    uly = request.GET.get('uly', 'BTC-USD')
    try:
        import requests
        url = 'https://www.okx.com/api/v5/public/instruments'
        resp = requests.get(url, params={'instType': 'OPTION', 'uly': uly}, proxies=get_proxy_dict(), timeout=15)
        result = resp.json()
        if result.get('code') != '0':
            return JsonResponse({'code': -1, 'error': result.get('msg', '')}, status=400)

        data = []
        for item in result.get('data', []):
            stk_raw = item.get('stk', '0')
            try:
                strike_val = float(stk_raw)
            except ValueError:
                strike_val = 0.0
            data.append({
                'inst_id': item.get('instId', ''),
                'uly': item.get('uly', ''),
                'opt_type': item.get('optType', ''),
                'strike': strike_val,
                'exp_time': int(item.get('expTime', 0)),
                'ct_val': item.get('ctVal', ''),
                'ct_mult': item.get('ctMult', ''),
                'settle_currency': item.get('settleCcy', ''),
            })
        return JsonResponse({'code': 0, 'data': data})
    except Exception as e:
        logger.warning(f"获取期权合约列表失败: {e}")
        return JsonResponse({'code': -1, 'error': str(e)}, status=500)


def api_option_ticker(request):
    """获取期权行情"""
    inst_id = request.GET.get('instId', '')
    if not inst_id:
        return JsonResponse({'code': -1, 'error': '缺少 instId 参数'}, status=400)
    try:
        import requests
        url = 'https://www.okx.com/api/v5/market/ticker'
        resp = requests.get(url, params={'instId': inst_id}, proxies=get_proxy_dict(), timeout=15)
        result = resp.json()
        if result.get('code') != '0':
            return JsonResponse({'code': -1, 'error': result.get('msg', '')}, status=400)

        items = result.get('data', [])
        if not items:
            return JsonResponse({'code': -1, 'error': '无数据'}, status=404)

        item = items[0]
        def _safe_float(v: str, fallback: float = 0.0) -> float:
            try: return float(v)
            except (ValueError, TypeError): return fallback
        return JsonResponse({'code': 0, 'data': {
            'inst_id': item.get('instId', ''),
            'last': _safe_float(item.get('last', '0')),
            'bid': _safe_float(item.get('bid', '0')),
            'ask': _safe_float(item.get('ask', '0')),
            'volume_24h': _safe_float(item.get('vol24h', '0')),
            'open_24h': _safe_float(item.get('open24h', '0')),
            'high_24h': _safe_float(item.get('high24h', '0')),
            'low_24h': _safe_float(item.get('low24h', '0')),
            'delta': _safe_float(item.get('delta', '0')),
            'gamma': _safe_float(item.get('gamma', '0')),
            'vega': _safe_float(item.get('vega', '0')),
            'theta': _safe_float(item.get('theta', '0')),
            'iv': _safe_float(item.get('optIv', '0')),
        }})
    except Exception as e:
        logger.warning(f"获取期权行情失败: {e}")
        return JsonResponse({'code': -1, 'error': str(e)}, status=500)


# ──────────────────────────────────────────────
# 旧版 api_positions — 保留兼容，重定向到新端点
# ──────────────────────────────────────────────

@csrf_exempt
def api_account_place_order(request):
    """下单"""
    if request.method != 'POST':
        return JsonResponse({'code': -1, 'error': '仅支持 POST'}, status=405)
    try:
        api_key, secret_key, passphrase, is_demo = _session_creds(request)
        creds = request.session.get('okx_credentials')
        if not creds.get('trade_permission'):
            return JsonResponse({'code': -1, 'error': '当前 API Key 无交易权限'}, status=403)

        data = json.loads(request.body)
        inst_id = data['instId']
        # 期权订单：直接使用 OKX 原始 ID（如 BTC-USD-260728-59000-C）
        if '-C' in inst_id or '-P' in inst_id:
            td_mode = data.get('tdMode', 'isolated')
            side = data['side']
            ord_type = data['ordType']
            sz = data['sz']
            px = data.get('px')
            result = post_order(
                api_key, secret_key, passphrase,
                inst_id=inst_id,
                td_mode=td_mode,
                side=side,
                ord_type=ord_type,
                sz=sz,
                px=px,
                is_demo=is_demo,
            )
        else:
            inst_id = ProtocolConverter.to_source_symbol(inst_id, 'okx')
            sz = data['sz']
            # OKX 市价买单 sz 为计价币数量，市价卖单 sz 为币数量
            if data['ordType'] == 'market' and data['side'] == 'buy' and data['tdMode'] == 'cash':
                ticker_resp = okx_api_request('GET', '/api/v5/market/ticker', api_key, secret_key, passphrase, params={'instId': inst_id}, is_demo=is_demo)
                if ticker_resp.get('code') != '0' or not ticker_resp.get('data'):
                    raise Exception(f"获取行情价格失败: {ticker_resp.get('msg', '未知错误')}")
                last = float(ticker_resp['data'][0].get('last', 0))
                if last <= 0:
                    raise Exception(f"无效行情价格: {last}")
                sz = str(round(float(sz) * last, 8))
            result = post_order(
                api_key, secret_key, passphrase,
                inst_id=inst_id,
                td_mode=data['tdMode'],
                side=data['side'],
                ord_type=data['ordType'],
                sz=sz,
                px=data.get('px'),
                pos_side=data.get('posSide'),
                lever=data.get('lever'),
                is_demo=is_demo,
            )
        return JsonResponse({'code': 0, 'data': result})
    except json.JSONDecodeError:
        return JsonResponse({'code': -1, 'error': '请求格式错误'}, status=400)
    except Exception as e:
        logger.error(f"下单失败: {e}")
        return JsonResponse({'code': -1, 'error': str(e)}, status=400)


@csrf_exempt
def api_account_cancel_order(request):
    """撤单"""
    if request.method != 'POST':
        return JsonResponse({'code': -1, 'error': '仅支持 POST'}, status=405)
    try:
        api_key, secret_key, passphrase, is_demo = _session_creds(request)
        creds = request.session.get('okx_credentials')
        if not creds.get('trade_permission'):
            return JsonResponse({'code': -1, 'error': '当前 API Key 无交易权限'}, status=403)

        data = json.loads(request.body)
        result = cancel_order(
            api_key, secret_key, passphrase,
            inst_id=data['instId'],
            ord_id=data['ordId'],
            is_demo=is_demo,
        )
        return JsonResponse({'code': 0, 'data': result})
    except json.JSONDecodeError:
        return JsonResponse({'code': -1, 'error': '请求格式错误'}, status=400)
    except Exception as e:
        logger.error(f"撤单失败: {e}")
        return JsonResponse({'code': -1, 'error': str(e)}, status=400)


def api_positions(request):
    """旧版仓位查询 — 使用 session 凭证"""
    return api_account_positions(request)


# ──────────────────────────────────────────────
# 策略管理 API
# ──────────────────────────────────────────────


@csrf_exempt
def api_strategies(request):
    """策略列表 & 创建"""
    if request.method == 'GET':
        from .models import Strategy
        strategies = Strategy.objects.all()
        return JsonResponse({'code': 0, 'data': [s.to_dict() for s in strategies]})

    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            from .models import Strategy
            strategy = Strategy.objects.create(
                type=data.get('type', 'dca'),
                symbol=data.get('symbol', 'BTCUSDT'),
                amount=data.get('amount', 10),
                interval_hours=data.get('interval_hours', 24),
                max_executions=data.get('max_executions', 0),
                name=data.get('name', ''),
                params=data.get('params', {}),
            )
            return JsonResponse({'code': 0, 'data': strategy.to_dict(), 'message': '策略已创建'})
        except Exception as e:
            return JsonResponse({'code': -1, 'error': str(e)}, status=400)

    return JsonResponse({'code': -1, 'error': '不支持的请求方法'}, status=405)


@csrf_exempt
def api_strategy_detail(request, strategy_id):
    """策略详情、更新状态、删除"""
    from .models import Strategy
    try:
        strategy = Strategy.objects.get(pk=strategy_id)
    except Strategy.DoesNotExist:
        return JsonResponse({'code': -1, 'error': '策略不存在'}, status=404)

    if request.method == 'GET':
        return JsonResponse({'code': 0, 'data': strategy.to_dict()})

    if request.method == 'PUT':
        try:
            import json
            data = json.loads(request.body)
            if 'status' in data:
                strategy.status = data['status']
            if 'amount' in data:
                strategy.amount = data['amount']
            if 'interval_hours' in data:
                strategy.interval_hours = data['interval_hours']
            if 'symbol' in data:
                strategy.symbol = data['symbol']
            if 'params' in data:
                strategy.params = data['params']
            strategy.save()
            return JsonResponse({'code': 0, 'data': strategy.to_dict(), 'message': '策略已更新'})
        except Exception as e:
            return JsonResponse({'code': -1, 'error': str(e)}, status=400)

    if request.method == 'DELETE':
        strategy.delete()
        return JsonResponse({'code': 0, 'message': '策略已删除'})

    return JsonResponse({'code': -1, 'error': '不支持的请求方法'}, status=405)
