"""
检测是否使用 TimescaleDB，如果是则创建 hypertable 并设置数据保留策略。

仅当 PostgreSQL 中安装了 timescaledb 扩展时执行。
如果扩展不可用，则静默跳过（使用普通 PostgreSQL）。
"""
from django.db import migrations


SQL_CHECK_EXTENSION = """
DO $$
BEGIN
    -- 检测 timescaledb 扩展是否已安装
    IF EXISTS (
        SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'
    ) THEN
        -- 创建扩展（如果尚未创建）
        CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

        -- 将 candlestick_cache 表转换为 hypertable
        PERFORM create_hypertable('candlestick_cache', 'time',
            chunk_time_interval => 604800, if_not_exists => TRUE);

        -- 设置数据保留策略
        PERFORM add_retention_policy('candlestick_cache',
            INTERVAL '30 days', if_not_exists => TRUE);
    END IF;
END
$$;
"""


class Migration(migrations.Migration):
    """为 CandlestickCache 创建 TimescaleDB hypertable（如可用）"""

    dependencies = [
        ('core', '0004_okxaccount_is_demo'),
    ]

    operations = [
        migrations.RunSQL(
            sql=SQL_CHECK_EXTENSION,
            reverse_sql=migrations.RunSQL.noop,
            # 仅在 PostgreSQL + TimescaleDB 环境下执行
            elidable=True,
        ),
    ]
