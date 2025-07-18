from django.urls import path
from . import views

urlpatterns = [
    path('conversations/', views.ConversationListView.as_view()),
    path('conversations/<int:conversation_id>/messages/', views.MessageListView.as_view()),
    path('conversations/start/', views.StartConversationView.as_view(), name='start-conversation'),

    path('my-groups/', views.MyGroupsListView.as_view(), name='my-group-list'),
    path('groups/discover/', views.PublicGroupListView.as_view(), name='public-group-list'),
    path('groups/create/', views.GroupCreateView.as_view(), name='group-create'),
    path('groups/<int:group_id>/request-join/', views.RequestToJoinGroupView.as_view(), name='request-join-group'),
]
