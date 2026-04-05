"""
WebSocket consumers for real-time session updates.

SessionConsumer      — /ws/session/<pk>/
    Used by session_monitor and session_join pages.
    Receives per-session events (ran_example, submitted, etc.)

GroupSessionConsumer — /ws/group/<group_pk>/session/
    Used by student/teacher dashboards.
    Receives group-level events (session_started, session_ended)
    so the dashboard updates in real-time without a page reload.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class SessionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_pk = self.scope['url_route']['kwargs']['session_pk']
        self.group_name = f'session_{self.session_pk}'

        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass  # read-only consumers; events come from Django views

    async def session_event(self, event):
        await self.send(text_data=json.dumps({
            'event': event['event'],
            'data':  event.get('data', {}),
        }))


class GroupSessionConsumer(AsyncWebsocketConsumer):
    """
    Dashboard-level consumer. Students connect once per group they belong to.
    When a teacher starts or ends a session, all connected students receive
    the event and their dashboard updates instantly.
    """
    async def connect(self):
        self.group_pk   = self.scope['url_route']['kwargs']['group_pk']
        self.group_name = f'group_session_{self.group_pk}'

        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass  # dashboard is read-only

    async def group_session_event(self, event):
        await self.send(text_data=json.dumps({
            'event': event['event'],
            'data':  event.get('data', {}),
        }))