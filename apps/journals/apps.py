# apps/journals/apps.py
from django.apps import AppConfig


class JournalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.journals' 

    def ready(self):
        import apps.journals.signals 