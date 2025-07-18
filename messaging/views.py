from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Count

# Import all necessary models and serializers from this app
from .models import Conversation, Message, Group, GroupJoinRequest
from .serializers import ConversationSerializer, MessageSerializer

# ===============================================================
# --- Direct Messaging Views ---
# ===============================================================

class StartConversationView(views.APIView):
    """
    Finds an existing 1-on-1 conversation with a user or creates a new one.
    Expects a POST request with the recipient's 'username'.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        recipient_username = request.data.get('username')
        if not recipient_username:
            return Response({'detail': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recipient = User.objects.get(username=recipient_username)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        if recipient == request.user:
            return Response({'detail': 'You cannot start a conversation with yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        # This is a robust way to find an existing 1-on-1 conversation.
        conversation = Conversation.objects.annotate(
            num_participants=Count('participants')
        ).filter(
            num_participants=2,
            participants=request.user
        ).filter(
            participants=recipient
        ).first()
        
        # If no conversation exists between the two, create a new one
        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, recipient)
            
        return Response({'conversation_id': conversation.id}, status=status.HTTP_200_OK)

class ConversationListView(generics.ListAPIView):
    """
    Returns a list of all conversations for the currently logged-in user.
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Returns all conversations where the current user is a participant
        return self.request.user.conversations.all().order_by('-updated_at')

class MessageListView(generics.ListAPIView):
    """
    Returns a list of all messages for a specific conversation.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        # This crucial check ensures a user can only see messages from conversations they are part of.
        conversation = get_object_or_404(self.request.user.conversations, id=conversation_id)
        return Message.objects.filter(conversation=conversation).order_by('-timestamp')

# ===============================================================
# --- Group Management Views ---
# ===============================================================

from .permissions import IsContentCreator   
from .serializers import GroupSerializer, GroupJoinRequestSerializer
from rest_framework.permissions import AllowAny
from rest_framework import generics
from django.contrib.auth.models import AnonymousUser
from rest_framework import status


class MyGroupsListView(generics.ListAPIView):
    """
    GET: Lists all groups the current user is a member of.
    """
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.joined_groups.all().order_by('name')

class GroupCreateView(generics.CreateAPIView):
    """
    POST: Creates a new group (restricted to Content Creators).
    """
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, IsContentCreator]

    def perform_create(self, serializer):
        group = serializer.save(creator=self.request.user)
        group.members.add(self.request.user) # The creator is automatically a member

class PublicGroupListView(generics.ListAPIView):
    """
    GET: Lists all public groups for discovery, allows searching.
    """
    serializer_class = GroupSerializer
    permission_classes = [AllowAny] # Anyone can search for groups

    def get_queryset(self):
        queryset = Group.objects.filter(is_premium=False)
        name_query = self.request.query_params.get('name')
        if name_query:
            queryset = queryset.filter(name__icontains=name_query)
        return queryset

class GroupJoinRequestView(views.APIView):
    """
    POST: Handles a user's request to join a group.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        if group.members.filter(id=request.user.id).exists():
            return Response({'detail': 'You are already a member of this group.'}, status=status.HTTP_400_BAD_REQUEST)
        if GroupJoinRequest.objects.filter(user=request.user, group=group, status='pending').exists():
            return Response({'detail': 'You have already sent a join request.'}, status=status.HTTP_400_BAD_REQUEST)
        
        GroupJoinRequest.objects.create(user=request.user, group=group)
        return Response({'status': 'request_sent'}, status=status.HTTP_201_CREATED)

class ManageJoinRequestsView(generics.UpdateAPIView):
    """
    PATCH: Allows a group creator to approve or reject a join request.
    """
    queryset = GroupJoinRequest.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        # Ensure the current user is the creator of the group for this request
        obj = super().get_object()
        if obj.group.creator != self.request.user:
            self.permission_denied(self.request)
        return obj

    def patch(self, request, *args, **kwargs):
        join_request = self.get_object()
        action = request.data.get('action') # 'approve' or 'reject'

        if action == 'approve':
            join_request.status = 'approved'
            join_request.group.members.add(join_request.user)
            join_request.save()
            return Response({'status': 'approved'})
        elif action == 'reject':
            join_request.status = 'rejected'
            join_request.save()
            return Response({'status': 'rejected'})
        
        return Response({'detail': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)

class RequestToJoinGroupView(views.APIView):
    """
    POST: Handles a user's request to join a group.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        if group.members.filter(id=request.user.id).exists():
            return Response({'detail': 'You are already a member of this group.'}, status=status.HTTP_400_BAD_REQUEST)
        if GroupJoinRequest.objects.filter(user=request.user, group=group, status='pending').exists():
            return Response({'detail': 'You have already sent a join request.'}, status=status.HTTP_400_BAD_REQUEST)
        
        GroupJoinRequest.objects.create(user=request.user, group=group)
        return Response({'status': 'request_sent'}, status=status.HTTP_201_CREATED)
