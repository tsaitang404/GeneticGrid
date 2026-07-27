from django.db import models


class OKXAccount(models.Model):
    label = models.CharField(max_length=64, help_text="用户命名，如'只读Key'")
    api_key = models.CharField(max_length=128, unique=True, help_text="OKX API Key")
    encrypted_secret_key = models.BinaryField(help_text="Fernet 加密的 Secret Key")
    encrypted_passphrase = models.BinaryField(help_text="Fernet 加密的 Passphrase")
    passphrase_hash = models.CharField(max_length=256, help_text="bcrypt 哈希（用于登陆校验）")
    account_info = models.JSONField(null=True, blank=True, help_text="注册时拉取的账户信息缓存")
    note = models.CharField(max_length=128, blank=True, default='', help_text="权限备注(只读/交易/网格等)")
    is_demo = models.BooleanField(default=False, help_text="是否为模拟盘(OKX Demo)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'okx_account'
        verbose_name = 'OKX 账户'
        verbose_name_plural = 'OKX 账户'

    def __str__(self):
        return f"{self.label} ({self.api_key[:8]}...)"


class CandlestickCache(models.Model):
    """K线数据缓存表"""
    
    # 复合主键字段
    source = models.CharField(max_length=20, db_index=True, help_text="数据源: binance, okx, tradingview等")
    symbol = models.CharField(max_length=20, db_index=True, help_text="交易对: BTC-USDT")
    mode = models.CharField(max_length=16, db_index=True, default='spot', help_text="交易模式: spot/contract")
    bar = models.CharField(max_length=10, db_index=True, help_text="时间周期: 1m, 5m, 1H, 1D等")
    time = models.BigIntegerField(db_index=True, help_text="K线时间戳(秒)")
    
    # K线数据
    open = models.DecimalField(max_digits=20, decimal_places=8, help_text="开盘价")
    high = models.DecimalField(max_digits=20, decimal_places=8, help_text="最高价")
    low = models.DecimalField(max_digits=20, decimal_places=8, help_text="最低价")
    close = models.DecimalField(max_digits=20, decimal_places=8, help_text="收盘价")
    volume = models.DecimalField(max_digits=30, decimal_places=8, help_text="成交量")
    
    # 元数据
    created_at = models.DateTimeField(auto_now_add=True, help_text="缓存时间")
    updated_at = models.DateTimeField(auto_now=True, help_text="更新时间")
    
    class Meta:
        db_table = 'candlestick_cache'
        # 联合唯一索引
        unique_together = [['source', 'symbol', 'mode', 'bar', 'time']]
        # 联合索引用于查询
        indexes = [
            models.Index(fields=['source', 'symbol', 'mode', 'bar', 'time'], name='cstick_src_mode_time_idx'),
            models.Index(fields=['source', 'symbol', 'mode', 'bar', '-time'], name='cstick_src_mode_desc_idx'),  # 倒序索引用于最新数据查询
        ]
        ordering = ['time']
        verbose_name = 'K线缓存'
        verbose_name_plural = 'K线缓存'
    
    def __str__(self):
        return f"{self.source}_{self.symbol}_{self.mode}_{self.bar}_{self.time}"


class ProxySettings(models.Model):
    """代理配置持久化（单行表，仅有一条记录）"""

    enabled = models.BooleanField(default=False, help_text="是否启用代理")
    container_auto_host = models.BooleanField(default=True, help_text="容器中自动将 127.0.0.1 映射为宿主机地址")
    container_host = models.CharField(max_length=256, default='host.docker.internal', help_text="容器访问宿主机别名")
    preferred_type = models.CharField(max_length=10, default='http', help_text="首选代理类型: http / socks5")

    socks5_host = models.CharField(max_length=256, default='127.0.0.1', help_text="SOCKS5 代理主机")
    socks5_port = models.IntegerField(default=1080, help_text="SOCKS5 代理端口")

    http_host = models.CharField(max_length=256, default='127.0.0.1', help_text="HTTP 代理主机")
    http_port = models.IntegerField(default=8080, help_text="HTTP 代理端口")

    updated_at = models.DateTimeField(auto_now=True, help_text="更新时间")

    class Meta:
        db_table = 'proxy_settings'
        verbose_name = '代理配置'
        verbose_name_plural = '代理配置'

    def __str__(self):
        return f"Proxy({'ON' if self.enabled else 'OFF'}) {self.preferred_type}://{self.get_host()}:{self.get_port()}"

    def get_host(self) -> str:
        cfg = {'http': self.http_host, 'socks5': self.socks5_host}
        return cfg.get(self.preferred_type, '127.0.0.1')

    def get_port(self) -> int:
        cfg = {'http': self.http_port, 'socks5': self.socks5_port}
        return cfg.get(self.preferred_type, 1080)

    def to_dict(self) -> dict:
        return {
            'enabled': self.enabled,
            'container_auto_host': self.container_auto_host,
            'container_host': self.container_host,
            'preferred_type': self.preferred_type,
            'socks5': {'host': self.socks5_host, 'port': self.socks5_port},
            'http': {'host': self.http_host, 'port': self.http_port},
        }

    @classmethod
    def load(cls) -> 'ProxySettings':
        """获取（或创建）唯一的代理配置记录"""
        obj, _ = cls.objects.get_or_create(pk=1, defaults={
            'enabled': False,
            'container_auto_host': True,
            'container_host': 'host.docker.internal',
            'preferred_type': 'http',
            'socks5_host': '127.0.0.1', 'socks5_port': 1080,
            'http_host': '127.0.0.1', 'http_port': 8080,
        })
        return obj
