"""创建交易策略表"""
from django.db import migrations, models


class Migration(migrations.Migration):
    """为 Strategy 创建表"""

    dependencies = [
        ('core', '0006_proxysettings'),
    ]

    operations = [
        migrations.CreateModel(
            name='Strategy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('dca', '定投 DCA'), ('grid', '网格交易')], max_length=20, help_text='策略类型')),
                ('status', models.CharField(choices=[('running', '运行中'), ('paused', '已暂停'), ('stopped', '已停止')], default='running', max_length=20, help_text='策略状态')),
                ('name', models.CharField(blank=True, default='', max_length=128, help_text='策略名称')),
                ('symbol', models.CharField(default='BTCUSDT', max_length=20, help_text='交易对')),
                ('amount', models.DecimalField(decimal_places=8, default=10, max_digits=20, help_text='每期投入金额 (USDT)')),
                ('interval_hours', models.IntegerField(default=24, help_text='执行间隔（小时）')),
                ('max_executions', models.IntegerField(default=0, help_text='最大执行次数（0=不限）')),
                ('executed_count', models.IntegerField(default=0, help_text='已执行次数')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_run_at', models.DateTimeField(blank=True, null=True)),
                ('next_run_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'strategy',
                'verbose_name': '交易策略',
                'verbose_name_plural': '交易策略',
                'ordering': ['-created_at'],
            },
        ),
    ]
