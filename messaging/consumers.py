import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User, AnonymousUser
from .models import Conversation, Message, Group
from .serializers import MessageSerializer

from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken

@sync_to_async
def get_user_from_token(token_key):
    try:
        if not token_key: return AnonymousUser()
        token = AccessToken(token_key)
        user_id = token.payload['user_id']
        return User.objects.get(id=user_id)
    except (InvalidToken, User.DoesNotExist):
        return AnonymousUser()

# ===============================================================
# --- Consumer for One-on-One Chats ---
# ===============================================================
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        token = dict(x.split("=") for x in query_string.split("&")).get('token', None)
        self.user = await get_user_from_token(token)

        if not self.user.is_authenticated or not await self.is_user_participant():
            await self.close(); return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data.get('message')
        new_message = await self.create_message(self.user, message_text)
        
        if new_message:
            serialized_message = MessageSerializer(new_message).data
            await self.channel_layer.group_send(
                self.room_group_name,
                { 'type': 'chat_message', 'message': serialized_message }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['message']))
        
    @sync_to_async
    def is_user_participant(self):
        return Conversation.objects.filter(id=self.conversation_id, participants=self.user).exists()

    @sync_to_async
    def create_message(self, sender, message_text):
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(conversation=conversation, sender=sender, text=message_text)
        conversation.save()
        return message

# ===============================================================
# --- Consumer for Group Chats ---
# ===============================================================
class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f'group_chat_{self.group_id}'
        
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        token = dict(x.split("=") for x in query_string.split("&")).get('token', None)
        self.user = await get_user_from_token(token)

        if not self.user.is_authenticated or not await self.is_user_member():
            await self.close(); return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data.get('message')
        new_message = await self.create_group_message(self.user, message_text)
        
        if new_message:
            serialized_message = MessageSerializer(new_message).data
            await self.channel_layer.group_send(
                self.room_group_name,
                { 'type': 'chat_message', 'message': serialized_message }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['message']))

    @sync_to_async
    def is_user_member(self):
        return Group.objects.filter(id=self.group_id, members=self.user).exists()

    @sync_to_async
    def create_group_message(self, sender, message_text):
        group = Group.objects.get(id=self.group_id)
        message = Message.objects.create(group=group, sender=sender, text=message_text)
        return message
