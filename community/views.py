from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Post, Like, Comment, PostBookmark
from .serializers import PostSerializer, CommentSerializer
from .permissions import IsContentCreator

class PostListCreateView(generics.ListCreateAPIView):
    queryset = Post.objects.all().order_by('-created_at')  # Order by newest first
    serializer_class = PostSerializer
    permission_classes = [IsContentCreator]

    def perform_create(self, serializer):
        content_type = 'TEXT'
        file = self.request.data.get('file')
        if file:
            if file.content_type.startswith('image'):
                content_type = 'IMAGE'
            elif file.content_type.startswith('video'):
                content_type = 'VIDEO'
            elif file.content_type == 'application/pdf':
                content_type = 'PDF'
        serializer.save(author=self.request.user, content_type=content_type)

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