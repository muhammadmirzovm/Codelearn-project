from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/test/(?P<test_pk>\d+)/$', consumers.TestConsumer.as_asgi()),
    re_path(r'ws/group/(?P<group_pk>\d+)/test/$', consumers.GroupTestConsumer.as_asgi()),
]
