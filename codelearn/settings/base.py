"""
Base settings for CodeLearn platform.
"""
import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    USE_DOCKER_SANDBOX=(bool, False),
)

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key-change-in-production')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = [
    'mondaycodelearn.fly.dev',
    'localhost',
    '127.0.0.1',
]
CSRF_TRUSTED_ORIGINS = [
    'https://mondaycodelearn.fly.dev',
]

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',

    'channels',
    'crispy_forms',
    'crispy_tailwind',
    'rosetta',

    'apps.users',
    'apps.tasks',
    'apps.sessions_app',
    'apps.submissions',
    'apps.runner',
    'apps.journals',
    'apps.support',
    'apps.resources',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'codelearn.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.users.context_processors.notifications', 
            ],
        },
    },
]

ASGI_APPLICATION = 'codelearn.asgi.application'
WSGI_APPLICATION = 'codelearn.wsgi.application'

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('ru', 'Русский'),
    ('uz', "O'zbek"),
]
LOCALE_PATHS = [
    BASE_DIR / 'locale',                        # global
    BASE_DIR / 'apps/journals/locale',
    BASE_DIR / 'apps/runner/locale',
    BASE_DIR / 'apps/sessions_app/locale',
    BASE_DIR / 'apps/submissions/locale',
    BASE_DIR / 'apps/tasks/locale',
    BASE_DIR / 'apps/users/locale',
    BASE_DIR / 'apps/resources/locale',
]
USE_I18N = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_ROOT = BASE_DIR / 'public'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/users/login/'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

# Redis / Channels
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Sandbox settings
USE_DOCKER_SANDBOX = env('USE_DOCKER_SANDBOX')
SANDBOX_IMAGE = env('SANDBOX_IMAGE', default='codelearn-runner:latest')
SANDBOX_TIMEOUT = int(env('SANDBOX_TIMEOUT', default='10'))        # seconds
SANDBOX_MEMORY_LIMIT = env('SANDBOX_MEMORY_LIMIT', default='64m')
SANDBOX_CPU_PERIOD = 100000
SANDBOX_CPU_QUOTA = 50000   # 50% of one CPU

# Code size limit (bytes)
MAX_CODE_SIZE = 64 * 1024  # 64 KB

# Rate limiting (requests per minute per student)
RUN_RATE_LIMIT = 10
SUBMIT_RATE_LIMIT = 5

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
