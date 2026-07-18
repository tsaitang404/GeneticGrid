# -*- coding: utf-8 -*-
"""
插件代理注入器

根据插件的 requires_proxy 配置，自动为旧服务注入代理支持。
"""

import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ProxyInjector:
    """代理注入器 - 为插件服务提供统一的代理支持"""
    
    _proxy_session = None  # 带代理的 session
    _direct_session = None  # 不带代理的 session
    
    @classmethod
    def get_session(cls, requires_proxy: bool = False) -> requests.Session:
        """
        获取 requests.Session 实例
        
        Args:
            requires_proxy: 是否需要代理
        
        Returns:
            requests.Session 实例（根据配置决定是否使用代理）
        """
        if requires_proxy:
            return cls._get_proxy_session()
        else:
            return cls._get_direct_session()
    
    @classmethod
    def _get_proxy_session(cls) -> requests.Session:
        """获取带代理的 session（复用单例）"""
        if cls._proxy_session is None:
            cls._proxy_session = cls._create_session(use_proxy=True)
            logger.info("🔐 创建带代理的 requests session")
        return cls._proxy_session
    
    @classmethod
    def _get_direct_session(cls) -> requests.Session:
        """获取不带代理的 session（复用单例）"""
        if cls._direct_session is None:
            cls._direct_session = cls._create_session(use_proxy=False)
            logger.info("🌐 创建直连 requests session")
        return cls._direct_session
    
    @classmethod
    def _create_session(cls, use_proxy: bool = False) -> requests.Session:
        """
        创建 requests.Session 实例
        
        Args:
            use_proxy: 是否配置代理
        
        Returns:
            配置好的 session 实例
        """
        session = requests.Session()
        
        # 配置重试策略
        retry = Retry(
            total=2,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=retry
        )
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        
        # 如果需要代理，配置代理
        if use_proxy:
            try:
                from core.proxy_config import configure_requests_proxies
                proxies = configure_requests_proxies(session)
                if proxies:
                    logger.info(f"✅ 已为 session 配置代理: {list(proxies.keys())}")
                else:
                    logger.warning("⚠️ 代理配置失败或代理不可用，将使用直连")
            except Exception as e:
                logger.warning(f"⚠️ 配置代理时出错: {e}，将使用直连")
        
        return session
    
    @classmethod
    def reset(cls):
        """重置所有 session（用于测试或重新加载配置）"""
        if cls._proxy_session:
            cls._proxy_session.close()
            cls._proxy_session = None
        if cls._direct_session:
            cls._direct_session.close()
            cls._direct_session = None
        logger.info("🔄 已重置所有 session")


def inject_proxy_to_service(service_instance, requires_proxy: bool = False):
    """
    为旧服务实例注入代理支持
    
    Args:
        service_instance: 服务实例（如 OKXMarketService）
        requires_proxy: 是否需要代理
    """
    service_class_name = service_instance.__class__.__name__
    
    # OKX 服务使用 SDK，代理通过构造函数传入，不需要后期注入
    if service_class_name == 'OKXMarketService':
        proxy_status = "🔐 OKX SDK 代理" if service_instance.proxy else "⚠️ OKX 无代理"
        logger.debug(f"{service_class_name} - {proxy_status}: {service_instance.proxy}")
        return
    
    # 其他服务使用 requests.Session
    if hasattr(service_instance, 'session'):
        # 替换 session
        service_instance.session = ProxyInjector.get_session(requires_proxy)
        proxy_status = "🔐 已启用代理" if requires_proxy else "🌐 直连模式"
        logger.debug(f"{service_class_name} - {proxy_status}")
    else:
        logger.warning(f"⚠️ {service_class_name} 没有 session 属性，无法注入代理")
