from rest_framework.permissions import BasePermission

class IsContentCreator(BasePermission):
    """
    Custom permission to only allow users marked as content creators to post.
    """
    def has_permission(self, request, view):
        # Allow anyone to view the posts (GET request)
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # For creating a post (POST), check if the user is a content creator
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'userprofile') and 
            request.user.userprofile.is_content_creator
        )
