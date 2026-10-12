"""
Production settings for Render and Fly.io deployment.
"""
from .base import *  # noqa
import os
import dj_database_url

DEBUG = False
SECRET_KEY = env('SECRET_KEY')

ALLOWED_HOSTS = [
    'mondaycodelearn.fly.dev',
    os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'codelearn.onrender.com'),
    'localhost',
    '127.0.0.1',
]

CSRF_TRUSTED_ORIGINS = [
    'https://mondaycodelearn.fly.dev',
    'https://' + os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'codelearn.onrender.com'),
]

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=DATABASE_URL.startswith(('postgres://', 'postgresql://')),
            conn_health_checks=True,
        )
    }
else:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured('DATABASE_URL is required in production.')

# ── Redis / Channels ──────────────────────────────────────────────────────────
REDIS_URL = env('REDIS_URL', default='')

if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        },
    }
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
else:
    # No Redis → use in-memory channels (polling fallback handles the rest)
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# ── Static files ──────────────────────────────────────────────────────────────
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

# ── Security ──────────────────────────────────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

USE_DOCKER_SANDBOX = False
CODE_EXECUTION_ENABLED = False
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
