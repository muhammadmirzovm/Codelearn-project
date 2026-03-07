"""
WSGI config for CodeLearn.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn.settings')
application = get_wsgi_application()
