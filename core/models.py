from django.db import models


class CandlestickCache(models.Model):
    """K线数据缓存表"""
    
    # 复合主键字段
    source = models.CharField(max_length=20, db_index=True, help_text="数据源: binance, okx, tradingview等")
    symbol = models.CharField(max_length=20, db_index=True, help_text="交易对: BTC-USDT")
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
        unique_together = [['source', 'symbol', 'bar', 'time']]
        # 联合索引用于查询
        indexes = [
            models.Index(fields=['source', 'symbol', 'bar', 'time']),
            models.Index(fields=['source', 'symbol', 'bar', '-time']),  # 倒序索引用于最新数据查询
        ]
        ordering = ['time']
        verbose_name = 'K线缓存'
        verbose_name_plural = 'K线缓存'
    
    def __str__(self):
        return f"{self.source}_{self.symbol}_{self.bar}_{self.time}"
