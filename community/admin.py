
from django.contrib import admin
from .models import Post, Tag, Like, Comment

admin.site.register(Post)
admin.site.register(Tag)
admin.site.register(Like)
admin.site.register(Comment)

