import json
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'change-me-to-a-secure-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# 代理配置
# 支持环境变量：
#   SOCKS5_PROXY_HOST (默认: 127.0.0.1)
#   SOCKS5_PROXY_PORT (默认: 1080)
#   HTTP_PROXY_HOST (默认: 127.0.0.1)
#   HTTP_PROXY_PORT (默认: 8080)
PROXY_ENABLED = os.environ.get('PROXY_ENABLED', 'true').lower() in ('true', '1', 'yes')
SOCKS5_PROXY_HOST = os.environ.get('SOCKS5_PROXY_HOST', '127.0.0.1')
SOCKS5_PROXY_PORT = int(os.environ.get('SOCKS5_PROXY_PORT', 1080))
HTTP_PROXY_HOST = os.environ.get('HTTP_PROXY_HOST', '127.0.0.1')
HTTP_PROXY_PORT = int(os.environ.get('HTTP_PROXY_PORT', 8080))

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

# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,  # 增加超时时间到20秒
        },
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
_raw_realtime_streams = os.environ.get('REALTIME_INGESTION_STREAMS')
if _raw_realtime_streams:
    try:
        parsed = json.loads(_raw_realtime_streams)
        if isinstance(parsed, list):
            REALTIME_INGESTION_STREAMS = parsed
    except json.JSONDecodeError:
        fallback = []
        for item in _raw_realtime_streams.split(','):
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
        REALTIME_INGESTION_STREAMS = fallback
