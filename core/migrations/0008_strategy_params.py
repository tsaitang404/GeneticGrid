"""为 Strategy 添加 params JSONField"""
from django.db import migrations, models


class Migration(migrations.Migration):
    """为 Strategy 添加 params 字段"""

    dependencies = [
        ('core', '0007_strategy'),
    ]

    operations = [
        migrations.AddField(
            model_name='strategy',
            name='params',
            field=models.JSONField(blank=True, default=dict, help_text='策略参数（JSON），如追踪止损的距离/方向等'),
        ),
    ]
