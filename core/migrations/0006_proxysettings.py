"""创建代理配置持久化表"""
from django.db import migrations, models


class Migration(migrations.Migration):
    """为 ProxySettings 创建表"""

    dependencies = [
        ('core', '0005_timescaledb_setup'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProxySettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=False, help_text='是否启用代理')),
                ('container_auto_host', models.BooleanField(default=True, help_text='容器中自动将 127.0.0.1 映射为宿主机地址')),
                ('container_host', models.CharField(default='host.docker.internal', max_length=256, help_text='容器访问宿主机别名')),
                ('preferred_type', models.CharField(default='http', max_length=10, help_text='首选代理类型: http / socks5')),
                ('socks5_host', models.CharField(default='127.0.0.1', max_length=256, help_text='SOCKS5 代理主机')),
                ('socks5_port', models.IntegerField(default=1080, help_text='SOCKS5 代理端口')),
                ('http_host', models.CharField(default='127.0.0.1', max_length=256, help_text='HTTP 代理主机')),
                ('http_port', models.IntegerField(default=8080, help_text='HTTP 代理端口')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='更新时间')),
            ],
            options={
                'db_table': 'proxy_settings',
                'verbose_name': '代理配置',
                'verbose_name_plural': '代理配置',
            },
        ),
        migrations.RunSQL(
            # 插入默认配置行（pk=1）
            sql="INSERT INTO proxy_settings (id, enabled, container_auto_host, container_host, preferred_type, socks5_host, socks5_port, http_host, http_port, updated_at) VALUES (1, false, true, 'host.docker.internal', 'http', '127.0.0.1', 1080, '127.0.0.1', 8080, NOW()) ON CONFLICT (id) DO NOTHING;",
            reverse_sql=migrations.RunSQL.noop,
            elidable=True,
        ),
    ]
