from django.urls import path
from . import views

urlpatterns = [
    path('posts/', views.PostListCreateView.as_view(), name='post-list-create'),
    path('posts/<int:pk>/like/', views.PostLikeView.as_view(), name='post-like'),
    path('posts/<int:pk>/bookmark/', views.PostBookmarkView.as_view(), name='post-bookmark'),
    path('posts/<int:pk>/comments/', views.CommentListCreateView.as_view(), name='post-comments'),
    path('user-posts/<str:username>/', views.UserPostListView.as_view(), name='user-post-list'),

]