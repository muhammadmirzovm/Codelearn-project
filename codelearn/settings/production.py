"""
Production settings - uses PostgreSQL and Docker sandbox.
"""
from .base import *  # noqa
import environ

env = environ.Env()

DEBUG = False

DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres://codelearn:codelearn@db:5432/codelearn')
}

USE_DOCKER_SANDBOX = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
