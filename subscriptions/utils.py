from django.utils import timezone
from .models import Subscription, Plan
from rest_framework.exceptions import PermissionDenied

def get_active_subscription(user):
    """
    Returns the active subscription of the user if it exists and is valid.
    """
    return Subscription.objects.filter(
        user=user,
        status__in=('active', 'trialing'),
        end_date__gt=timezone.now()
    ).order_by('-end_date').first()

def get_user_entitlement(user, feature_key, default_value=None):
    """
    Retrieves a feature value from the user's active subscription plan features.
    If no active subscription, returns default_value.
    """
    sub = get_active_subscription(user)
    if not sub:
        # Fallback for student type - default to 'student-free' plan features
        # If user is a student, we can look up the free plan features
        try:
            free_plan = Plan.objects.get(slug='student-free')
            return free_plan.features.get(feature_key, default_value)
        except Plan.DoesNotExist:
            return default_value
    
    return sub.plan.features.get(feature_key, default_value)

def is_feature_enabled(user, feature_key):
    """
    Returns True if a boolean feature is enabled for the user's plan.
    """
    return bool(get_user_entitlement(user, feature_key, False))

def check_institute_student_limit(institute):
    """
    Checks if an institute has reached its plan's student limit.
    Returns True if allowed to add more, False if limit exceeded.
    """
    # Find active subscription of the institute owner
    sub = get_active_subscription(institute.owner)
    if not sub:
        # If no active subscription, default limit is 0 (Starter has 100)
        limit = 0
    else:
        limit = sub.plan.student_limit or 999999
        
    current_count = institute.members.count()
    return current_count < limit

def subscription_required(feature_key=None):
    """
    Decorator for API views to enforce active subscriptions or specific plan features.
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required.")
                
            sub = get_active_subscription(request.user)
            if not sub:
                raise PermissionDenied("An active paid subscription is required to access this feature.")
                
            if feature_key and not is_feature_enabled(request.user, feature_key):
                raise PermissionDenied("Your current plan does not include this feature.")
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
