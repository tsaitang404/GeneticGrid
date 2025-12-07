"""
缓存管理命令

用于查看、清理和管理Redis缓存
"""
from django.core.management.base import BaseCommand
from core.unified_cache import get_cache_manager
from core.redis_cache import redis_cache_enabled


class Command(BaseCommand):
    help = '管理Redis缓存数据'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['stats', 'clear', 'clear-all'],
            help='操作类型: stats(统计), clear(清除特定类型), clear-all(清除所有)'
        )
        parser.add_argument(
            '--type',
            type=str,
            help='数据类型: candlestick, funding_rate, funding_history, basis, basis_history, ticker'
        )
        parser.add_argument(
            '--pattern',
            type=str,
            help='Redis key模式 (例如: funding_rate:okx:*)'
        )

    def handle(self, *args, **options):
        if not redis_cache_enabled():
            self.stdout.write(self.style.ERROR('❌ Redis缓存未启用'))
            return

        action = options['action']
        manager = get_cache_manager()

        if action == 'stats':
            self.show_stats(manager)
        elif action == 'clear':
            self.clear_cache(manager, options.get('type'), options.get('pattern'))
        elif action == 'clear-all':
            self.clear_all(manager)

    def show_stats(self, manager):
        """显示缓存统计信息"""
        self.stdout.write(self.style.SUCCESS('\n📊 缓存统计信息\n'))
        
        stats = manager.get_cache_stats()
        if not stats:
            self.stdout.write(self.style.WARNING('无法获取统计信息'))
            return
        
        total = sum(stats.values())
        self.stdout.write(f"{'数据类型':<25} {'缓存条目数':>12}")
        self.stdout.write('-' * 40)
        
        for data_type, count in stats.items():
            self.stdout.write(f"{data_type:<25} {count:>12}")
        
        self.stdout.write('-' * 40)
        self.stdout.write(self.style.SUCCESS(f"{'总计':<25} {total:>12}\n"))

    def clear_cache(self, manager, data_type, pattern):
        """清除特定缓存"""
        if pattern:
            self.stdout.write(f'🗑️  清除模式: {pattern}')
            deleted = manager.clear_all(pattern)
        elif data_type:
            pattern_map = {
                'candlestick': 'candles:*',
                'funding_rate': 'funding_rate:*',
                'funding_history': 'funding_history:*',
                'basis': 'basis:*',
                'basis_history': 'basis_history:*',
                'ticker': 'ticker:*'
            }
            pattern = pattern_map.get(data_type)
            if not pattern:
                self.stdout.write(self.style.ERROR(f'❌ 未知的数据类型: {data_type}'))
                return
            
            self.stdout.write(f'🗑️  清除类型: {data_type}')
            deleted = manager.clear_all(pattern)
        else:
            self.stdout.write(self.style.ERROR('❌ 请指定 --type 或 --pattern'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'✅ 已清除 {deleted} 个缓存条目'))

    def clear_all(self, manager):
        """清除所有缓存"""
        self.stdout.write(self.style.WARNING('⚠️  将清除所有缓存数据'))
        confirm = input('确认继续? (yes/no): ')
        
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('已取消'))
            return
        
        deleted = manager.clear_all()
        self.stdout.write(self.style.SUCCESS(f'✅ 已清除 {deleted} 个缓存条目'))
