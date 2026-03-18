import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn.settings')

django_asgi_app = get_asgi_application()

from apps.sessions_app import routing as session_routing
from apps.users.consumers import GroupChatConsumer, PresenceConsumer

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            session_routing.websocket_urlpatterns + [
                path('ws/chat/<int:group_id>/', GroupChatConsumer.as_asgi()),
                path('ws/presence/',            PresenceConsumer.as_asgi()),
            ]
        )
    ),
})