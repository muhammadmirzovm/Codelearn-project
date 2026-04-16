import json
from channels.generic.websocket import AsyncWebsocketConsumer


class TestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.test_pk = self.scope['url_route']['kwargs']['test_pk']
        self.group_name = f'test_{self.test_pk}'
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def test_event(self, event):
        await self.send(text_data=json.dumps({
            'event': event['event'],
            'data':  event.get('data', {}),
        }))


class GroupTestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_pk = self.scope['url_route']['kwargs']['group_pk']
        self.group_name = f'group_test_{self.group_pk}'
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def group_test_event(self, event):
        await self.send(text_data=json.dumps({
            'event': event['event'],
            'data':  event.get('data', {}),
        }))
