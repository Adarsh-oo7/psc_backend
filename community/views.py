from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Post, Like, Comment, PostBookmark
from .serializers import PostSerializer, CommentSerializer
from .permissions import IsContentCreator

# In community/views.py
from .models import Post, Tag # Make sure Tag is imported


import logging

logger = logging.getLogger(__name__)

class PostListCreateView(generics.ListCreateAPIView):
    queryset = Post.objects.all().order_by('-created_at')
    serializer_class = PostSerializer
    permission_classes = [IsContentCreator]

    def perform_create(self, serializer):
        try:
            # Get the uploaded file
            file = self.request.FILES.get('file')
            
            # Determine content type from file
            content_type = 'TEXT'
            if file:
                if file.content_type.startswith('image/'):
                    content_type = 'IMAGE'
                elif file.content_type.startswith('video/'):
                    content_type = 'VIDEO'
                elif file.content_type == 'application/pdf':
                    content_type = 'PDF'
                else:
                    logger.warning(f"Unknown file type: {file.content_type}")
            
            # Save the post with the file and content_type
            post = serializer.save(
                author=self.request.user, 
                content_type=content_type,
                file=file  # This is the key line that was missing!
            )
            
            # Handle tags
            tags_str = self.request.data.get('tags_input', '')
            if tags_str:
                tag_names = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                for name in tag_names:
                    tag, created = Tag.objects.get_or_create(name=name.lower())
                    post.tags.add(tag)
                    
            logger.info(f"Post created successfully: {post.id}")
            
        except Exception as e:
            logger.error(f"Error creating post: {str(e)}")
            raise


class PostLikeView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        
        if not created:
            like.delete()
            liked = False
            message = 'Post unliked'
        else:
            liked = True
            message = 'Post liked'
        
        # Return updated counts for frontend
        return Response({
            'status': 'liked' if liked else 'unliked',
            'message': message,
            'likes_count': post.likes.count(),
            'is_liked': liked
        })

class PostBookmarkView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        bookmark, created = PostBookmark.objects.get_or_create(user=request.user, post=post)
        
        if not created:
            bookmark.delete()
            bookmarked = False
            message = 'Post unbookmarked'
        else:
            bookmarked = True
            message = 'Post bookmarked'
        
        return Response({
            'status': 'bookmarked' if bookmarked else 'unbookmarked',
            'message': message,
            'is_bookmarked': bookmarked
        })

class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        return Comment.objects.filter(post_id=self.kwargs['pk']).order_by('-created_at')
    
    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs['pk'])
        serializer.save(author=self.request.user, post=post)
    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # Return updated comment count
        post = get_object_or_404(Post, pk=self.kwargs['pk'])
        response.data['comments_count'] = post.comments.count()
        return response
    

from rest_framework import generics
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from .models import Post
from .serializers import PostSerializer
from rest_framework.permissions import AllowAny
class UserPostListView(generics.ListAPIView):
    """
    Returns a list of all posts created by a specific user.
    """
    serializer_class = PostSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Look up the user by the username passed in the URL
        username = self.kwargs['username']
        user = get_object_or_404(User, username=username)
        return Post.objects.filter(author=user).order_by('-created_at')