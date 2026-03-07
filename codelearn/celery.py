"""
Celery application factory for CodeLearn.
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn.settings')

app = Celery('codelearn')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
