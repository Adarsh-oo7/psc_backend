from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Post(models.Model):
    CONTENT_CHOICES = [
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
        ('PDF', 'PDF'),
        ('TEXT', 'Text'),
    ]
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=5, choices=CONTENT_CHOICES)
    # The file field can hold images, videos, or PDFs
    file = models.FileField(upload_to='community_posts/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        # A user can only like a post once
        unique_together = ('user', 'post')

class Comment(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class PostBookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')

    class Meta:
        unique_together = ('user', 'post')
