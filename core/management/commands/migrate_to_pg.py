"""
从 SQLite 迁移 K 线数据到 PostgreSQL（一次性迁移工具）

在首次切换到 PostgreSQL 时运行此命令，将现有的 SQLite
历史 K 线数据导入到 PostgreSQL。

用法:
    python manage.py migrate_to_pg                    # 全量迁移
    python manage.py migrate_to_pg --source okx       # 仅迁移指定数据源
    python manage.py migrate_to_pg --batch 10000      # 每批 10000 条

注意:
    - 运行此命令前，请确保 DATABASE_URL 已指向目标 PostgreSQL
    - 运行此命令后，后续的实时数据会直接写入 PostgreSQL
"""
import time

from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS

from core.models import CandlestickCache


class Command(BaseCommand):
    help = '从 SQLite 导入历史 K 线数据到 PostgreSQL（一次性迁移）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source', type=str, default='',
            help='仅迁移指定数据源'
        )
        parser.add_argument(
            '--symbol', type=str, default='',
            help='仅迁移指定交易对'
        )
        parser.add_argument(
            '--bar', type=str, default='',
            help='仅迁移指定时间周期'
        )
        parser.add_argument(
            '--batch', type=int, default=10000,
            help='每批迁移条数（默认 10000）'
        )

    def handle(self, *args, **options):
        source_db = DEFAULT_DB_ALIAS
        target_db_alias = 'target'

        # 检查当前是否已连接到 PostgreSQL
        from django.db import connections
        target_vendor = connections.databases.get('default', {}).get('ENGINE', '')
        if 'postgresql' not in target_vendor:
            self.stdout.write(self.style.WARNING(
                '⚠️  当前 default 数据库不是 PostgreSQL，跳过迁移。\n'
                '   设置 DATABASE_URL 环境变量后重试。'
            ))
            return

        # 检查源数据库（SQLite）是否有数据
        filters = {}
        if options['source']:
            filters['source'] = options['source']
        if options['symbol']:
            filters['symbol'] = options['symbol']
        if options['bar']:
            filters['bar'] = options['bar']

        total = CandlestickCache.objects.using(source_db).filter(**filters).count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ SQLite 中没有需要迁移的数据，直接使用 PostgreSQL'))
            return

        self.stdout.write(f'\n📦 待迁移数据: {total:,} 行')
        self.stdout.write('   源库: SQLite')
        self.stdout.write('   目标: PostgreSQL')
        self.stdout.write('')

        batch_size = options['batch']
        migrated = 0
        start_time = time.time()
        last_pk = 0

        # 检查目标库是否已有数据
        try:
            last_obj = CandlestickCache.objects.using(target_db_alias).order_by('-pk').first()
            if last_obj:
                last_pk = last_obj.pk
                self.stdout.write(f'   🔄 目标库已有数据，从 PK={last_pk} 之后继续导入')
                filters['pk__gt'] = last_pk
        except Exception:
            pass

        queryset = CandlestickCache.objects.using(source_db).filter(**filters).order_by('pk')

        while True:
            batch = list(queryset.filter(pk__gt=last_pk)[:batch_size])
            if not batch:
                break

            objs_to_create = []
            for obj in batch:
                objs_to_create.append(CandlestickCache(
                    source=obj.source,
                    symbol=obj.symbol,
                    mode=obj.mode,
                    bar=obj.bar,
                    time=obj.time,
                    open=obj.open,
                    high=obj.high,
                    low=obj.low,
                    close=obj.close,
                    volume=obj.volume,
                    created_at=obj.created_at,
                    updated_at=obj.updated_at,
                ))
                last_pk = obj.pk

            try:
                CandlestickCache.objects.using(target_db_alias).bulk_create(
                    objs_to_create, ignore_conflicts=True
                )
                migrated += len(objs_to_create)
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'   ❌ 批量写入失败 (PK={last_pk}): {e}'
                ))
                raise

            elapsed = time.time() - start_time
            rate = migrated / elapsed if elapsed > 0 else 0
            self.stdout.write(
                f'   ✅ 已迁移 {migrated:,}/{total:,} 行 '
                f'({rate:.0f} 行/秒)'
            )

        elapsed = time.time() - start_time
        summary = (
            f'\n🎉 迁移完成!\n'
            f'   迁移: {migrated:,} 行\n'
            f'   耗时: {elapsed:.1f} 秒\n'
        )
        if migrated > 0:
            summary += f'   速度: {migrated/elapsed:.0f} 行/秒'
        self.stdout.write(self.style.SUCCESS(summary))
