from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Session-level (monitor + join pages)
    re_path(r'ws/session/(?P<session_pk>\d+)/$', consumers.SessionConsumer.as_asgi()),
    # Group-level (dashboard real-time updates)
    re_path(r'ws/group/(?P<group_pk>\d+)/session/$', consumers.GroupSessionConsumer.as_asgi()),
]