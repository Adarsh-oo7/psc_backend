from rest_framework.permissions import BasePermission

class IsContentCreator(BasePermission):
    """
    Custom permission to only allow users marked as content creators
    to perform certain actions, like creating posts or groups.
    """
    def has_permission(self, request, view):
        # First, check if the user is authenticated at all.
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Then, check if they have a user profile and if the
        # 'is_content_creator' flag is set to True.
        return hasattr(request.user, 'userprofile') and request.user.userprofile.is_content_creator
