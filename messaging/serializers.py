from rest_framework import serializers
from .models import Conversation, Message
from questionbank.serializers import UserSerializer

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    class Meta:
        model = Message
        fields = ['id', 'sender', 'text', 'timestamp']

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = MessageSerializer(source='messages.last', read_only=True)
    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'last_message', 'updated_at']

from .models import Group, GroupJoinRequest

class GroupSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    member_count = serializers.IntegerField(source='members.count', read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'creator', 'member_count', 'is_premium']

class GroupJoinRequestSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    group = GroupSerializer(read_only=True)

    class Meta:
        model = GroupJoinRequest
        fields = ['id', 'user', 'group', 'status', 'requested_at']
