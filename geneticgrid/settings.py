import json
import os
from pathlib import Path
from typing import Any

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'change-me-to-a-secure-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# 支持环境变量：ALLOWED_HOSTS=example.com,127.0.0.1
_allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()] or ['127.0.0.1', 'localhost', '38.76.190.84']

# CIDR 网段白名单（通过 ALLOWED_CIDR_NETS 环境变量配置）
# 格式: 10.126.126.0/24,192.168.1.0/24
_allowed_cidr_env = os.environ.get('ALLOWED_CIDR_NETS', '').strip()
if _allowed_cidr_env:
    ALLOWED_CIDR_NETS = [n.strip() for n in _allowed_cidr_env.split(',') if n.strip()]
else:
    ALLOWED_CIDR_NETS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'allow_cidr.middleware.AllowCIDRMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS settings
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = 'geneticgrid.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # 不再需要模板目录，使用 Vue SPA
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'geneticgrid.wsgi.application'
ASGI_APPLICATION = 'geneticgrid.asgi.application'

# Database — PostgreSQL (TimescaleDB)
# https://docs.djangoproject.com/en/stable/ref/settings/#databases
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
if not DATABASE_URL:
    raise RuntimeError(
        'DATABASE_URL 环境变量未设置。\n'
        '请配置 PostgreSQL 连接，例如:\n'
        '  DATABASE_URL=postgres://geneticgrid:geneticgrid@localhost:5432/geneticgrid\n'
        '或在 .env 文件中配置。'
    )

import urllib.parse
parsed = urllib.parse.urlparse(DATABASE_URL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': parsed.path.lstrip('/') or 'geneticgrid',
        'USER': parsed.username or 'geneticgrid',
        'PASSWORD': parsed.password or 'geneticgrid',
        'HOST': parsed.hostname or 'localhost',
        'PORT': parsed.port or 5432,
        'OPTIONS': {'connect_timeout': 10},
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Additional locations for static files
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 实时采集服务配置
REALTIME_INGESTION_AUTO_START = os.environ.get(
    'REALTIME_INGESTION_AUTO_START',
    'true'
).lower() in ('true', '1', 'yes')

REALTIME_INGESTION_STREAMS = [
    {'source': 'okx', 'symbol': 'BTCUSDT', 'bar': '1s'},
    {'source': 'okx', 'symbol': 'BTCUSDT', 'bar': '1m'},
    {'source': 'okx', 'symbol': 'ETHUSDT', 'bar': '1s'},
    {'source': 'okx', 'symbol': 'ETHUSDT', 'bar': '1m'},
]


def _strip_wrapping_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_realtime_ingestion_streams(raw_value: str) -> list[dict[str, Any]]:
    """解析实时采集配置，兼容 JSON 和冒号分隔格式。"""
    normalized = _strip_wrapping_quotes(raw_value)

    try:
        parsed = json.loads(normalized)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    fallback = []
    for item in normalized.split(','):
        parts = [p.strip() for p in item.split(':') if p.strip()]
        if not parts:
            continue
        stream = {
            'source': parts[0],
            'symbol': parts[1] if len(parts) > 1 else 'BTCUSDT',
            'bar': parts[2] if len(parts) > 2 else '1s'
        }
        if len(parts) > 3:
            stream['poll_interval'] = float(parts[3])
        if len(parts) > 4:
            stream['batch_size'] = int(parts[4])
        fallback.append(stream)
    return fallback


_raw_realtime_streams = os.environ.get('REALTIME_INGESTION_STREAMS')
if _raw_realtime_streams:
    REALTIME_INGESTION_STREAMS = parse_realtime_ingestion_streams(_raw_realtime_streams)

# Redis 缓存配置（热数据缓存层，降低数据库查询压力）
REDIS_CACHE_ENABLED = os.environ.get('REDIS_CACHE_ENABLED', 'false').lower() in ('true', '1', 'yes')
REDIS_CACHE_URL = os.environ.get('REDIS_CACHE_URL', 'redis://127.0.0.1:6379/0')
REDIS_CACHE_TTL_SECONDS = int(os.environ.get('REDIS_CACHE_TTL_SECONDS', 86400))  # 默认1天
REDIS_CACHE_MAX_ENTRIES = int(os.environ.get('REDIS_CACHE_MAX_ENTRIES', 5000))

# K 线数据保留天数（-1 表示永久保留）
DB_RETENTION_DAYS = int(os.environ.get('DB_RETENTION_DAYS', '30'))

# 插件 HTTP 请求超时（秒）
PLUGIN_HTTP_TIMEOUT = int(os.environ.get('PLUGIN_HTTP_TIMEOUT', '60'))
