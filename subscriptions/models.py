from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Plan(models.Model):
    PLAN_TYPE_CHOICES = [
        ('student', 'Student'),
        ('institute', 'Institute'),
    ]
    INTERVAL_CHOICES = [
        ('month', 'Monthly'),
        ('year', 'Annual'),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES)
    user_type = models.CharField(max_length=10, choices=PLAN_TYPE_CHOICES)
    features = models.JSONField(default=dict, help_text="Entitlements map, e.g. {'student_limit': 100, 'feed_limit': 15}")
    student_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Max students allowed (for Institute plans)")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_user_type_display()})"


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('trialing', 'Trialing'),
        ('expired', 'Expired'),
        ('canceled', 'Canceled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='trialing')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    trial_end = models.DateTimeField(null=True, blank=True)
    razorpay_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    customer_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_active(self):
        # Checks if subscription is active or trialing, and not expired
        now = timezone.now()
        if self.status in ('active', 'trialing'):
            if self.end_date > now:
                return True
        return False

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"


class PaymentHistory(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscription_payments')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment of {self.amount} by {self.user.username} ({self.status})"
