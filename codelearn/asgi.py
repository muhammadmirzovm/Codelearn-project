"""
ASGI config for CodeLearn – supports HTTP and WebSocket via Django Channels.
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn.settings')

django_asgi_app = get_asgi_application()

from apps.sessions_app import routing as session_routing  # noqa – import after setup

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            session_routing.websocket_urlpatterns
        )
    ),
})
