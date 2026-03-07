try:
    from .celery import app as celery_app  # noqa
    __all__ = ('celery_app',)
except ImportError:
    pass  # Celery not installed — fine for dev mode
