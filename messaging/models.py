from django.db import models
from django.contrib.auth.models import User

# ===============================================================
# --- Group Models ---
# ===============================================================

class Group(models.Model):
    """
    Represents a study group created by a Community User.
    """
    name = models.CharField(max_length=100, unique=True) # Ensure group names are unique
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    
    # CORRECTED: Use 'joined_groups' to match the API view
    members = models.ManyToManyField(User, related_name='joined_groups', blank=True)
    
    is_premium = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GroupJoinRequest(models.Model):
    """
    Tracks a Normal User's request to join a specific group.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_join_requests')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='join_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
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

