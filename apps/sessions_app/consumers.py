"""
WebSocket consumer for real-time session updates.

Students and teachers connect to ws://host/ws/session/<pk>/
and receive JSON events:
  { "event": "session_started"|"student_joined"|"ran_example"|"submitted"|"submission_result",
    "data": { ... } }
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class SessionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_pk = self.scope['url_route']['kwargs']['session_pk']
        self.group_name = f'session_{self.session_pk}'

        # Only authenticated users
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Receive message from WebSocket (client → server, e.g., heartbeat)
    async def receive(self, text_data):
        pass  # Students are read-only consumers; events come from Django views

    # Receive message from channel layer (server → WebSocket)
    async def session_event(self, event):
        await self.send(text_data=json.dumps({
            'event': event['event'],
            'data': event.get('data', {}),
        }))
