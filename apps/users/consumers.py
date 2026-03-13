import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from apps.users.models import ChatMessage
from apps.users.models import Group
from django.utils import timezone


def get_online_key(group_id):
    return f'online_users_group_{group_id}'


class GroupChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f'chat_{self.group_id}'
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Add user to online set in Redis
        await self.add_online_user()

        # Broadcast updated online list to everyone in the room
        await self.broadcast_online_users()

    async def disconnect(self, close_code):
        if hasattr(self, 'user') and not self.user.is_anonymous:
            await self.remove_online_user()
            await self.broadcast_online_users()

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'chat_message')

        if msg_type == 'chat_message':
            message = data.get('message', '').strip()
            if not message:
                return

            await self.save_message(self.user, message)

            now = timezone.localtime(timezone.now())
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'chat_message',
                'message': message,
                'sender': self.user.username,
                'time': now.strftime('%H:%M'),
            })

        elif msg_type == 'typing':
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'typing_indicator',
                'sender': self.user.username,
                'is_typing': data.get('is_typing', False),
            })

    # --- Event handlers ---

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
            'time': event.get('time', ''),
        }))

    async def online_users_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'online_users',
            'users': event['users'],
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender': event['sender'],
            'is_typing': event['is_typing'],
        }))

    # --- Helpers ---

    @database_sync_to_async
    def add_online_user(self):
        key = get_online_key(self.group_id)
        users = cache.get(key) or []
        if self.user.username not in users:
            users.append(self.user.username)
        cache.set(key, users, timeout=86400)

    @database_sync_to_async
    def remove_online_user(self):
        key = get_online_key(self.group_id)
        users = cache.get(key) or []
        if self.user.username in users:
            users.remove(self.user.username)
        cache.set(key, users, timeout=86400)

    @database_sync_to_async
    def get_online_users(self):
        key = get_online_key(self.group_id)
        return cache.get(key) or []

    async def broadcast_online_users(self):
        users = await self.get_online_users()
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'online_users_update',
            'users': users,
        })

    @database_sync_to_async
    def save_message(self, user, message):
        group = Group.objects.get(id=self.group_id)
        ChatMessage.objects.create(group=group, sender=user, message=message)