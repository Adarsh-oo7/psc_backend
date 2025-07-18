from django.db import models
from django.contrib.auth.models import User

# ===============================================================
# --- Group Models ---
# ===============================================================

class Group(models.Model):
    """
    Represents a study group created by a Community User.
    """
    name = models.CharField(max_length=255)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(User, related_name='chat_groups', blank=True)
    is_premium = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GroupJoinRequest(models.Model):
    """
    Tracks a Normal User's request to join a specific group.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_join_requests')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='join_requests')
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A user can only have one pending request for a specific group
        unique_together = ('user', 'group')

# ===============================================================
# --- Direct Messaging Models ---
# ===============================================================

class Conversation(models.Model):
    """
    Represents a one-on-one conversation between two users.
    """
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Message(models.Model):
    """
    Represents a single message within a conversation.
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']

