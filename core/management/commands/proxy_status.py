"""
Django 管理命令：检查和配置代理
使用方法: python manage.py proxy_status
"""

from django.core.management.base import BaseCommand
from core.proxy_config import print_proxy_status


class Command(BaseCommand):
    help = '检查和显示代理配置状态'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test',
            action='store_true',
            help='测试代理连接',
        )

    def handle(self, *args, **options):
        print_proxy_status()
        
        if options['test']:
            self.test_proxy()
    
    def test_proxy(self):
        """测试代理的实际功能"""
        print("\n=== 代理功能测试 ===\n")
        
        try:
            import httpx
            from core.proxy_config import get_proxy_url
            
            proxy = get_proxy_url('http')
            if not proxy:
                self.stdout.write(self.style.WARNING("❌ HTTP 代理不可用，跳过测试"))
                return
            
            self.stdout.write(f"✅ 使用代理 {proxy} 进行测试")
            
            # 测试百度
            print("测试百度...")
            with httpx.Client(proxy=proxy, timeout=10, verify=False) as client:
                response = client.get('https://www.baidu.com')
                print(f"✅ 百度 (HTTP {response.status_code})")
            
            # 测试 OKX 官网
            print("测试 OKX 官网...")
            with httpx.Client(proxy=proxy, timeout=10, verify=False) as client:
                response = client.get('https://www.okx.com')
                print(f"✅ OKX 官网 (HTTP {response.status_code})")
            
            # 测试 OKX API
            print("测试 OKX Public API...")
            with httpx.Client(proxy=proxy, timeout=10, verify=False) as client:
                response = client.get('https://www.okx.com/api/v5/public/time')
                print(f"✅ OKX API (HTTP {response.status_code})")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   服务器时间: {data.get('data', [{}])[0].get('ts', 'N/A')}")
            
            self.stdout.write(self.style.SUCCESS("\n✅ 所有代理功能测试通过"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ 代理功能测试失败: {e}"))
            import traceback
            traceback.print_exc()
