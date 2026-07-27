"""
清理过期的 K 线缓存数据

用法:
    python manage.py prune_candles                  # 清理 30 天前的数据
    python manage.py prune_candles --days 7          # 清理 7 天前的数据
    python manage.py prune_candles --days -1         # 禁用（跳过）
    python manage.py prune_candles --dry-run         # 仅预览，不删除
    python manage.py prune_candles --source okx      # 仅清理指定数据源
    python manage.py prune_candles --symbol BTCUSDT  # 仅清理指定交易对
"""
import time
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Min
from django.utils import timezone

from core.models import CandlestickCache


class Command(BaseCommand):
    help = '清理超过保留天数的历史 K 线数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=None,
            help='保留天数（覆盖 settings.DB_RETENTION_DAYS，设为 -1 跳过清理）'
        )
        parser.add_argument(
            '--source', type=str, default='',
            help='仅清理指定数据源（如 okx, binance）'
        )
        parser.add_argument(
            '--symbol', type=str, default='',
            help='仅清理指定交易对（如 BTCUSDT）'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='仅预览将要删除的数量，不实际删除'
        )
        parser.add_argument(
            '--chunk-size', type=int, default=10000,
            help='每批删除的行数（默认 10000，避免长时间锁表）'
        )

    def handle(self, *args, **options):
        days = options['days'] if options['days'] is not None else getattr(
            settings, 'DB_RETENTION_DAYS', 30
        )

        if days < 0:
            self.stdout.write(self.style.WARNING('⚠️  数据保留已禁用（--days=-1），跳过清理'))
            return

        cutoff = timezone.now() - timedelta(days=days)
        cutoff_ts = int(cutoff.timestamp())
        dry_run = options['dry_run']
        chunk_size = options['chunk_size']

        # 构建过滤条件
        filters = {'time__lt': cutoff_ts}
        label_parts = [f'早于 {cutoff.strftime("%Y-%m-%d")} ({days} 天前)']
        if options['source']:
            filters['source'] = options['source']
            label_parts.append(f"source={options['source']}")
        if options['symbol']:
            filters['symbol'] = options['symbol']
            label_parts.append(f"symbol={options['symbol']}")

        # 检查是否有数据需要清理
        total_count = CandlestickCache.objects.filter(**filters).count()
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('✅ 没有需要清理的数据'))
            return

        # 获取日期范围信息
        date_range = CandlestickCache.objects.filter(**filters).aggregate(
            earliest=Min('time')
        )
        earliest_ts = date_range['earliest']
        if earliest_ts:
            earliest_dt = datetime.fromtimestamp(earliest_ts, tz=timezone.utc)
            label_parts.append(f"最早数据: {earliest_dt.strftime('%Y-%m-%d')}")

        label = ' | '.join(label_parts)
        self.stdout.write(f"\n📊 {label}")
        self.stdout.write(f"   待清理行数: {total_count:,}")

        if dry_run:
            self.stdout.write(self.style.WARNING('   ⚠️  --dry-run 模式，未实际删除'))
            return

        confirm = input(f'\n⚠️  确认删除 {total_count:,} 行历史数据? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('已取消'))
            return

        deleted_total = 0
        start_time = time.time()

        while True:
            # 每次取 chunk_size 条 ID 进行删除
            ids = list(
                CandlestickCache.objects.filter(**filters)
                .values_list('pk', flat=True)[:chunk_size]
            )
            if not ids:
                break

            deleted, _ = CandlestickCache.objects.filter(pk__in=ids).delete()
            deleted_total += deleted

            elapsed = time.time() - start_time
            rate = deleted_total / elapsed if elapsed > 0 else 0
            self.stdout.write(
                f"   🗑️  已删除 {deleted_total:,} 行 "
                f"({rate:.0f} 行/秒) "
                f"[{deleted_total}/{total_count}]"
            )

        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ 清理完成: 共删除 {deleted_total:,} 行 (耗时 {elapsed:.1f} 秒)'
        ))
