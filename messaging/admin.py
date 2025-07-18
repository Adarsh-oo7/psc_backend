from django.contrib import admin
from .models import Conversation, Message, Group, GroupJoinRequest
# Register your models here.
admin.site.register(Conversation)
admin.site.register(Message)    
admin.site.register(Group)
admin.site.register(GroupJoinRequest)
