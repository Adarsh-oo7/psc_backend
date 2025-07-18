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



from .models import Tag # Make sure Tag is imported

class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tags_input = serializers.CharField(
        write_only=True, 
        required=False, 
        allow_blank=True,
        help_text="Comma-separated list of tags."
    )
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    is_liked_by_user = serializers.SerializerMethodField()
    is_bookmarked_by_user = serializers.SerializerMethodField()
    file = serializers.FileField(required=False)  # Add this line to handle file uploads

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'title', 'content_type', 'file', 'created_at', 
            'tags', 'tags_input', 'likes_count', 'comments_count', 
            'is_liked_by_user', 'is_bookmarked_by_user'
        ]
        read_only_fields = ['author', 'content_type']

    def create(self, validated_data):
        """
        Custom create method to handle the 'tags_input' field and file upload.
        """
        # Pop the tags_input data from the validated data
        tags_data = validated_data.pop('tags_input', '')
        
        # Create the Post instance with the remaining data (including file)
        post = Post.objects.create(**validated_data)
        
        # Process the tags string
        if tags_data:
            tag_names = [name.strip() for name in tags_data.split(',')]
            for name in tag_names:
                if name:
                    tag, _ = Tag.objects.get_or_create(name=name.lower())
                    post.tags.add(tag)
                    
        return post

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

    # --- THIS IS THE CRITICAL FIX ---


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
