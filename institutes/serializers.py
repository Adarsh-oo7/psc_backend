from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction

from .models import Institute, Message, FeeStructure, PaymentTransaction, FeeItem, Payment, InstituteJoinRequest
from questionbank.models import UserProfile
# We import UserSerializer which is simple and doesn't cause a loop
from questionbank.serializers import UserSerializer

# ===================================================================
# --- Institute and Student Serializers ---
# ===================================================================

class InstituteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institute
        fields = [
            'id', 'name', 'logo', 'contact_email',
            'login_bg_image', 'login_image_1', 'login_image_2', 'login_image_3'
        ]
        read_only_fields = ['id']

# institutes/serializers.py

class StudentCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    # --- NEW: Add first_name and last_name ---
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name'] # Add new fields
        read_only_fields = ['id']

    def create(self, validated_data):
        institute = self.context['institute']
        with transaction.atomic():
            # The User model's create_user method handles these fields automatically
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                password=validated_data['password'],
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', '')
            )
            UserProfile.objects.create(user=user, institute=institute)
        return user

# ===================================================================
# --- Messaging Serializers ---
# ===================================================================

class MessageCreateSerializer(serializers.ModelSerializer):
    recipients = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, write_only=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Message
        fields = ['id', 'subject', 'body', 'recipients', 'image']

    def create(self, validated_data):
        recipient_users = validated_data.pop('recipients')
        message = Message.objects.create(**validated_data)
        message.recipients.set(recipient_users)
        return message

class ReceivedMessageSerializer(serializers.ModelSerializer):
    institute = serializers.StringRelatedField() 
    class Meta:
        model = Message
        fields = ['id', 'subject', 'body', 'image', 'sent_at', 'read_by', 'institute']

# ===================================================================
# --- Fee and Payment Serializers ---
# ===================================================================

class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = '__all__'

class FeeStructureSerializer(serializers.ModelSerializer):
    transactions = PaymentTransactionSerializer(many=True, read_only=True)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    balance_due = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = FeeStructure
        fields = [
            'id', 'student_profile', 'total_fees', 'due_date', 
            'amount_paid', 'balance_due', 'transactions'
        ]

# ===================================================================
# --- Join Request Serializer ---
# ===================================================================

class JoinRequestSerializer(serializers.ModelSerializer):
    # CORRECTED: Instead of nesting the full UserProfileSerializer (which causes an import loop),
    # we nest the simple UserSerializer by pointing to the source.
    user = UserSerializer(source='student_profile.user', read_only=True)

    class Meta:
        model = InstituteJoinRequest
        fields = ['id', 'user', 'institute', 'status', 'requested_at']
        read_only_fields = ['id', 'user', 'status', 'requested_at']



class FeeItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeItem
        fields = ['id', 'description', 'fee_type', 'amount', 'due_date', 'is_paid']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'amount', 'payment_date', 'payment_method', 'notes']

class StudentFeeDashboardSerializer(serializers.Serializer):
    """A custom serializer to combine all fee data into one response."""
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    outstanding_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    fees = FeeItemSerializer(many=True)
    payments = PaymentSerializer(many=True)