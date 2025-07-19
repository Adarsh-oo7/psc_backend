from django.contrib import admin
from .models import Conversation, Message, Group, GroupJoinRequest
# Register your models here.
from django.contrib import admin
from .models import Conversation, Message, Group, GroupJoinRequest

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'is_premium', 'created_at')
    search_fields = ('name', 'creator__username')
    list_filter = ('is_premium',)
    filter_horizontal = ('members',)

@admin.register(GroupJoinRequest)
class GroupJoinRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'status', 'requested_at')
    list_filter = ('status', 'group')
    search_fields = ('user__username', 'group__name')
    list_editable = ('status',)

admin.site.register(Conversation)
admin.site.register(Message)
