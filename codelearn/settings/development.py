"""
Development settings - uses SQLite and disables Docker sandbox.
"""
from .base import *  # noqa

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Use in-memory channel layer in dev (no Redis required for WebSockets)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Use subprocess runner in dev (no Docker)
USE_DOCKER_SANDBOX = False

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
