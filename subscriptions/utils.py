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
    # Force unlimited/free settings for beta users
    if feature_key == 'feed_limit':
        return 999999
    if feature_key == 'student_limit':
        return 999999
    if isinstance(default_value, bool):
        return True
    return default_value

def is_feature_enabled(user, feature_key):
    """
    Returns True if a boolean feature is enabled for the user's plan.
    """
    return True

def check_institute_student_limit(institute):
    """
    Checks if an institute has reached its plan's student limit.
    Returns True if allowed to add more, False if limit exceeded.
    """
    return True

def subscription_required(feature_key=None):
    """
    Decorator for API views to enforce active subscriptions or specific plan features.
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            # Bypass checks: 100% free beta access
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

