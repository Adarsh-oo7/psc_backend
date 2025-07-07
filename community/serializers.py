from rest_framework import serializers
from .models import Post, Tag, Like, Comment, PostBookmark
from questionbank.serializers import UserSerializer

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    class Meta:
        model = Comment
        fields = ['id', 'author', 'text', 'created_at']

class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    is_liked_by_user = serializers.SerializerMethodField()
    is_bookmarked_by_user = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'title', 
            'content_type', # <-- CORRECTED: This field is now included
            'file', 'created_at', 'tags', 
            'likes_count', 'comments_count', 
            'is_liked_by_user', 'is_bookmarked_by_user'
        ]

    def get_is_liked_by_user(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and obj.likes.filter(user=user).exists()

    def get_is_bookmarked_by_user(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and obj.bookmarks.filter(user=user).exists()

    def get_file(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            return request.build_absolute_uri(obj.file.url)
        return None
