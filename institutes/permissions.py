# institutes/permissions.py

from rest_framework.permissions import BasePermission

class IsInstituteOwner(BasePermission):
    """
    Custom permission to only allow owners of an institute to edit it or its resources.
    """

    def has_permission(self, request, view):
        # Allow access if the user is authenticated and owns an institute.
        # This protects list and create views.
        return request.user and request.user.is_authenticated and hasattr(request.user, 'owned_institute')

    def has_object_permission(self, request, view, obj):
        # Get the institute associated with the object being accessed.
        institute_of_object = None
        
        # Determine the institute from the object type
        if hasattr(obj, 'institute'):  # For UserProfile, Question, Topic
            institute_of_object = obj.institute
        elif hasattr(obj, 'owner'):  # For the Institute model itself
            # Check if obj.owner is the same as request.user
            return obj.owner == request.user
            
        # If the object has an institute, check if the user owns it.
        if institute_of_object:
            return institute_of_object.owner == request.user
            
        return False