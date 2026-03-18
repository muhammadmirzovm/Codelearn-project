import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from apps.users.models import ChatMessage, Group
from django.utils import timezone

SITE_ONLINE_KEY = 'site_online_users'


def unread_key(group_id, username):
    return f'chat_unread_{group_id}_{username}'


def user_channel(username):
    return f'user_{username}'


class PresenceConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
            return

        self.presence_group  = 'site_presence'
        self.user_group_name = user_channel(self.user.username)

        await self.channel_layer.group_add(self.presence_group,  self.channel_name)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()
        await self.mark_online()
        await self.notify_groups()

    async def disconnect(self, close_code):
        if hasattr(self, 'user') and not self.user.is_anonymous:
            await self.mark_offline()
            await self.notify_groups()
            await self.channel_layer.group_discard(self.presence_group,  self.channel_name)
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def badge_update(self, event):
        await self.send(text_data=json.dumps({
            'type':     'badge_update',
            'group_id': event['group_id'],
            'count':    event['count'],
        }))

    @database_sync_to_async
    def mark_online(self):
        users = cache.get(SITE_ONLINE_KEY) or set()
        if isinstance(users, list):
            users = set(users)
        users.add(self.user.username)
        cache.set(SITE_ONLINE_KEY, users, timeout=86400)

    @database_sync_to_async
    def mark_offline(self):
        users = cache.get(SITE_ONLINE_KEY) or set()
        if isinstance(users, list):
            users = set(users)
        users.discard(self.user.username)
        cache.set(SITE_ONLINE_KEY, users, timeout=86400)

    @database_sync_to_async
    def get_user_group_ids(self):
        if self.user.is_teacher:
            return list(self.user.taught_groups.values_list('id', flat=True))
        return list(self.user.student_groups.values_list('id', flat=True))

    async def notify_groups(self):
        group_ids = await self.get_user_group_ids()
        online    = await self.get_site_online()
        for gid in group_ids:
            members         = await self.get_group_members(gid)
            online_in_group = [u for u in online if u in members]
            await self.channel_layer.group_send(f'chat_{gid}', {
                'type':  'online_users_update',
                'users': online_in_group,
            })

    @database_sync_to_async
    def get_site_online(self):
        users = cache.get(SITE_ONLINE_KEY) or set()
        return list(users)

    @database_sync_to_async
    def get_group_members(self, group_id):
        try:
            group   = Group.objects.prefetch_related('students').select_related('teacher').get(id=group_id)
            members = set(group.students.values_list('username', flat=True))
            members.add(group.teacher.username)
            return members
        except Group.DoesNotExist:
            return set()


class GroupChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.group_id        = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f'chat_{self.group_id}'
        self.user            = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Reset unread in cache
        await self.reset_unread()

        # Push badge=0 to user's presence WS (other tabs/pages update instantly)
        await self.channel_layer.group_send(user_channel(self.user.username), {
            'type':     'badge_update',
            'group_id': self.group_id,
            'count':    0,
        })

        await self.broadcast_online_users()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data     = json.loads(text_data)
        msg_type = data.get('type', 'chat_message')

        if msg_type == 'chat_message':
            message = data.get('message', '').strip()
            if not message:
                return

            await self.save_message(self.user, message)
            await self.increment_and_push_badges()

            now      = timezone.localtime(timezone.now())
            months   = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
            time_str = f"{now.day} {months[now.month-1]} {now.strftime('%H:%M')}"

            await self.channel_layer.group_send(self.room_group_name, {
                'type':    'chat_message',
                'message': message,
                'sender':  self.user.username,
                'time':    time_str,
            })

        elif msg_type == 'typing':
            await self.channel_layer.group_send(self.room_group_name, {
                'type':      'typing_indicator',
                'sender':    self.user.username,
                'is_typing': data.get('is_typing', False),
            })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type':    'chat_message',
            'message': event['message'],
            'sender':  event['sender'],
            'time':    event.get('time', ''),
        }))

    async def online_users_update(self, event):
        await self.send(text_data=json.dumps({
            'type':  'online_users',
            'users': event['users'],
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type':      'typing',
            'sender':    event['sender'],
            'is_typing': event['is_typing'],
        }))

    async def broadcast_online_users(self):
        users = await self.get_online_in_group()
        await self.channel_layer.group_send(self.room_group_name, {
            'type':  'online_users_update',
            'users': users,
        })

    @database_sync_to_async
    def reset_unread(self):
        cache.set(unread_key(self.group_id, self.user.username), 0, timeout=86400 * 30)

    @database_sync_to_async
    def get_members_except_self(self):
        try:
            group   = Group.objects.prefetch_related('students').select_related('teacher').get(id=self.group_id)
            members = list(group.students.values_list('username', flat=True))
            members.append(group.teacher.username)
            return [u for u in members if u != self.user.username]
        except Group.DoesNotExist:
            return []

    async def increment_and_push_badges(self):
        others = await self.get_members_except_self()
        for username in others:
            new_count = await self.increment_unread(username)
            await self.channel_layer.group_send(user_channel(username), {
                'type':     'badge_update',
                'group_id': self.group_id,
                'count':    new_count,
            })

    @database_sync_to_async
    def increment_unread(self, username):
        key     = unread_key(self.group_id, username)
        current = cache.get(key) or 0
        new_val = current + 1
        cache.set(key, new_val, timeout=86400 * 30)
        return new_val

    @database_sync_to_async
    def get_online_in_group(self):
        site_online = cache.get(SITE_ONLINE_KEY) or set()
        if isinstance(site_online, list):
            site_online = set(site_online)
        try:
            group   = Group.objects.prefetch_related('students').select_related('teacher').get(id=self.group_id)
            members = set(group.students.values_list('username', flat=True))
            members.add(group.teacher.username)
            return [u for u in site_online if u in members]
        except Group.DoesNotExist:
            return []

    @database_sync_to_async
    def save_message(self, user, message):
        group = Group.objects.get(id=self.group_id)
        ChatMessage.objects.create(group=group, sender=user, message=message)