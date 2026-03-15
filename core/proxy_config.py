"""
代理配置模块
支持 SOCKS5 和 HTTP 代理，默认尝试连接 127.0.0.1:1080 (SOCKS5) 或 127.0.0.1:8080 (HTTP)
"""

import os
import logging
import socket
import time
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'true', '1', 'yes', 'on'}


def _is_container_environment() -> bool:
    if os.path.exists('/.dockerenv'):
        return True

    cgroup_path = Path('/proc/1/cgroup')
    if cgroup_path.exists():
        try:
            text = cgroup_path.read_text(encoding='utf-8', errors='ignore')
            if 'docker' in text or 'kubepods' in text or 'containerd' in text:
                return True
        except OSError:
            pass
    return False


# 全局代理选项（可通过 API 运行时更新）
PROXY_OPTIONS = {
    'enabled': _env_bool('PROXY_ENABLED', True),
    # 容器中若配置为 localhost，自动改为宿主机地址
    'container_auto_host': _env_bool('PROXY_CONTAINER_AUTO_HOST', True),
    'container_host': os.environ.get('PROXY_CONTAINER_HOST', 'host.docker.internal'),
}

# 代理配置
PROXY_CONFIG = {
    'socks5': {
        'host': os.environ.get('SOCKS5_PROXY_HOST', '127.0.0.1'),
        'port': int(os.environ.get('SOCKS5_PROXY_PORT', 1080)),
    },
    'http': {
        'host': os.environ.get('HTTP_PROXY_HOST', '127.0.0.1'),
        'port': int(os.environ.get('HTTP_PROXY_PORT', 8080)),
    },
}

# 代理可用性缓存 (避免每次请求都检测，提升性能)
# 格式: {proxy_type: (is_available, timestamp)}
_PROXY_CACHE = {}
_CACHE_TTL = 60  # 缓存60秒


def clear_proxy_cache() -> None:
    """清空代理可用性缓存。"""
    _PROXY_CACHE.clear()


def _resolve_proxy_host(host: str) -> str:
    is_local = host in {'127.0.0.1', 'localhost'}
    if not is_local:
        return host

    if PROXY_OPTIONS['container_auto_host'] and _is_container_environment():
        return PROXY_OPTIONS['container_host']

    return host


def _normalize_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError('端口必须为整数') from exc

    if not 1 <= port <= 65535:
        raise ValueError('端口必须在 1-65535 之间')
    return port


def get_proxy_settings_snapshot() -> Dict[str, Any]:
    """返回当前代理配置快照（用于设置页展示）。"""
    is_container = _is_container_environment()

    def _entry(proxy_type: str) -> Dict[str, Any]:
        config = PROXY_CONFIG[proxy_type]
        effective_host = _resolve_proxy_host(config['host'])
        return {
            'host': config['host'],
            'effective_host': effective_host,
            'port': config['port'],
            'available': is_proxy_available(proxy_type),
            'url': get_proxy_url(proxy_type),
        }

    return {
        'enabled': PROXY_OPTIONS['enabled'],
        'container_auto_host': PROXY_OPTIONS['container_auto_host'],
        'container_host': PROXY_OPTIONS['container_host'],
        'in_container': is_container,
        'http': _entry('http'),
        'socks5': _entry('socks5'),
        'proxy': get_proxy(),
    }


def update_proxy_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    """更新运行时代理配置。"""
    if not isinstance(payload, dict):
        raise ValueError('请求体必须为 JSON 对象')

    if 'enabled' in payload:
        PROXY_OPTIONS['enabled'] = bool(payload['enabled'])

    if 'container_auto_host' in payload:
        PROXY_OPTIONS['container_auto_host'] = bool(payload['container_auto_host'])

    if 'container_host' in payload and payload['container_host']:
        PROXY_OPTIONS['container_host'] = str(payload['container_host']).strip()

    for proxy_type in ('http', 'socks5'):
        if proxy_type not in payload:
            continue
        value = payload[proxy_type]
        if not isinstance(value, dict):
            raise ValueError(f'{proxy_type} 配置必须是对象')

        if 'host' in value and value['host']:
            PROXY_CONFIG[proxy_type]['host'] = str(value['host']).strip()
        if 'port' in value:
            PROXY_CONFIG[proxy_type]['port'] = _normalize_port(value['port'])

    clear_proxy_cache()
    return get_proxy_settings_snapshot()


def is_proxy_available(proxy_type: str = 'socks5') -> bool:
    """检查代理是否可用（带缓存，避免每次请求都检测）"""
    global _PROXY_CACHE

    if not PROXY_OPTIONS['enabled']:
        return False
    
    # 检查缓存
    now = time.time()
    if proxy_type in _PROXY_CACHE:
        is_available, timestamp = _PROXY_CACHE[proxy_type]
        if now - timestamp < _CACHE_TTL:
            return is_available
    
    # 缓存过期或不存在，重新检测
    try:
        config = PROXY_CONFIG.get(proxy_type)
        if not config:
            _PROXY_CACHE[proxy_type] = (False, now)
            return False
        
        host = _resolve_proxy_host(config['host'])
        port = config['port']
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            logger.info(f"✅ {proxy_type.upper()} 代理 {host}:{port} 可用")
            _PROXY_CACHE[proxy_type] = (True, now)
            return True
        else:
            logger.warning(f"❌ {proxy_type.upper()} 代理 {host}:{port} 不可用")
            _PROXY_CACHE[proxy_type] = (False, now)
            return False
    except Exception as e:
        logger.warning(f"❌ 检查 {proxy_type.upper()} 代理失败: {e}")
        _PROXY_CACHE[proxy_type] = (False, now)
        return False


def get_proxy_url(proxy_type: str = 'http') -> Optional[str]:
    """获取代理 URL
    
    Args:
        proxy_type: 代理类型 ('socks5' 或 'http')
    
    Returns:
        代理 URL 或 None (代理不可用)
    """
    if not is_proxy_available(proxy_type):
        return None
    
    config = PROXY_CONFIG.get(proxy_type)
    host = _resolve_proxy_host(config['host'])
    port = config['port']
    
    if proxy_type.lower() == 'socks5':
        return f"socks5://{host}:{port}"
    else:
        return f"http://{host}:{port}"


def get_proxy_dict() -> Dict[str, str]:
    """获取代理字典 (用于 requests/httpx)
    
    返回格式:
    {
        'http://': 'http://proxy_url',
        'https://': 'http://proxy_url',
    }
    """
    proxy_url = get_proxy_url('http')
    if proxy_url:
        # 移除 socks5:// 前缀，requests 使用特殊格式
        if proxy_url.startswith('socks5://'):
            proxy_url = 'socks5://' + proxy_url[9:]
        return {
            'http://': proxy_url,
            'https://': proxy_url,
        }
    return {}


def get_proxy() -> Optional[str]:
    """获取通用代理配置（用于所有需要代理的插件）
    
    支持:
    - HTTP/HTTPS 代理: 'http://host:port'
    - SOCKS5 代理: 'socks5://host:port'
    """
    if not PROXY_OPTIONS['enabled']:
        return None

    # 优先使用 HTTP 代理
    http_proxy = get_proxy_url('http')
    if http_proxy:
        return http_proxy
    
    # 降级到 SOCKS5
    socks5_proxy = get_proxy_url('socks5')
    if socks5_proxy:
        return socks5_proxy
    
    return None


def configure_requests_proxies(session=None) -> Optional[Dict[str, str]]:
    """为 requests.Session 配置代理
    
    Args:
        session: requests.Session 实例，如果为 None 则仅返回代理字典
    
    Returns:
        代理字典
    """
    proxies = get_proxy_dict()
    
    if session and proxies:
        session.proxies.update(proxies)
        logger.info(f"✅ 已为 requests session 配置代理")
    
    return proxies


def print_proxy_status():
    """打印代理状态"""
    print("\n=== 代理配置状态 ===")
    print(f"代理开关: {'✅ 启用' if PROXY_OPTIONS['enabled'] else '❌ 关闭'}")
    print(f"容器自动主机映射: {'✅ 启用' if PROXY_OPTIONS['container_auto_host'] else '❌ 关闭'}")
    print(f"容器主机别名: {PROXY_OPTIONS['container_host']}")
    print(f"当前在容器内: {'是' if _is_container_environment() else '否'}")
    
    # SOCKS5 状态
    socks5_available = is_proxy_available('socks5')
    socks5_config = PROXY_CONFIG['socks5']
    socks5_host = _resolve_proxy_host(socks5_config['host'])
    print(f"SOCKS5: {socks5_config['host']} -> {socks5_host}:{socks5_config['port']} - {'✅ 可用' if socks5_available else '❌ 不可用'}")
    
    # HTTP 状态
    http_available = is_proxy_available('http')
    http_config = PROXY_CONFIG['http']
    http_host = _resolve_proxy_host(http_config['host'])
    print(f"HTTP: {http_config['host']} -> {http_host}:{http_config['port']} - {'✅ 可用' if http_available else '❌ 不可用'}")
    
    # 实际使用的代理
    proxy = get_proxy()
    print(f"通用代理: {proxy or '未配置'}")
    
    proxy_dict = get_proxy_dict()
    print(f"Requests/HTTPX 代理: {proxy_dict or '未配置'}")
    
    print()
