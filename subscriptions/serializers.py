from rest_framework import serializers
from .models import Plan, Subscription, PaymentHistory
from django.contrib.auth import get_user_model

User = get_user_model()

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id', 'name', 'slug', 'price', 'currency', 'interval', 'user_type', 'features', 'student_limit', 'active']

class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.filter(active=True), source='plan', write_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = ['id', 'plan', 'plan_id', 'status', 'start_date', 'end_date', 'trial_end', 'is_active', 'created_at']
        read_only_fields = ['id', 'status', 'start_date', 'end_date', 'trial_end', 'created_at']

class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = ['id', 'amount', 'status', 'razorpay_payment_id', 'razorpay_order_id', 'created_at']
