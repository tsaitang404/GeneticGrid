"""
代理配置模块
支持 SOCKS5 和 HTTP 代理，默认尝试连接 127.0.0.1:1080 (SOCKS5) 或 127.0.0.1:8080 (HTTP)
"""

import os
import logging
import socket
import time
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# 代理配置
PROXY_CONFIG = {
    # SOCKS5 代理
    'socks5': {
        'host': os.environ.get('SOCKS5_PROXY_HOST', '127.0.0.1'),
        'port': int(os.environ.get('SOCKS5_PROXY_PORT', 1080)),
    },
    # HTTP/HTTPS 代理
    'http': {
        'host': os.environ.get('HTTP_PROXY_HOST', '127.0.0.1'),
        'port': int(os.environ.get('HTTP_PROXY_PORT', 8080)),
    }
}

# 代理可用性缓存 (避免每次请求都检测，提升性能)
# 格式: {proxy_type: (is_available, timestamp)}
_PROXY_CACHE = {}
_CACHE_TTL = 60  # 缓存60秒


def is_proxy_available(proxy_type: str = 'socks5') -> bool:
    """检查代理是否可用（带缓存，避免每次请求都检测）"""
    global _PROXY_CACHE
    
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
        
        host = config['host']
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
    host = config['host']
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
    
    # SOCKS5 状态
    socks5_available = is_proxy_available('socks5')
    socks5_config = PROXY_CONFIG['socks5']
    print(f"SOCKS5: {socks5_config['host']}:{socks5_config['port']} - {'✅ 可用' if socks5_available else '❌ 不可用'}")
    
    # HTTP 状态
    http_available = is_proxy_available('http')
    http_config = PROXY_CONFIG['http']
    print(f"HTTP: {http_config['host']}:{http_config['port']} - {'✅ 可用' if http_available else '❌ 不可用'}")
    
    # 实际使用的代理
    proxy = get_proxy()
    print(f"通用代理: {proxy or '未配置'}")
    
    proxy_dict = get_proxy_dict()
    print(f"Requests/HTTPX 代理: {proxy_dict or '未配置'}")
    
    print()
