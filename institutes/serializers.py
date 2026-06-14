from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction

from .models import Institute, Message, FeeItem, Payment, InstituteJoinRequest, Batch, BatchMembership, Attendance, Note
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
            'id', 'name', 'slug', 'logo', 'contact_email', 'tagline',
            'primary_color', 'accent_color', 'custom_domain', 'address',
            'phone', 'website', 'established_year',
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
        from subscriptions.utils import check_institute_student_limit
        if not check_institute_student_limit(institute):
            raise serializers.ValidationError("Your institute has reached its plan's student limit. Please upgrade your subscription.")
            
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

# (FeeStructure and PaymentTransaction serializers removed)

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
    status = serializers.CharField(read_only=True)
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = FeeItem
        fields = ['id', 'description', 'fee_type', 'amount', 'due_date', 'is_paid', 'status', 'total_paid']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'fee_item', 'amount', 'payment_date', 'payment_method', 'notes']

class StudentFeeDashboardSerializer(serializers.Serializer):
    """A custom serializer to combine all fee data into one response."""
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    outstanding_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    fees = FeeItemSerializer(many=True)
    payments = PaymentSerializer(many=True)


class BatchSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(source='memberships.count', read_only=True)

    class Meta:
        model = Batch
        fields = ['id', 'name', 'description', 'student_count', 'created_at']

class BatchDetailSerializer(serializers.ModelSerializer):
    students = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        fields = ['id', 'name', 'description', 'students', 'created_at']

    def get_students(self, obj):
        memberships = obj.memberships.select_related('student_profile__user')
        from questionbank.serializers import UserProfileSerializer
        return UserProfileSerializer([m.student_profile for m in memberships], many=True, context=self.context).data

class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student_profile.user.username', read_only=True)
    student_full_name = serializers.CharField(source='student_profile.user.get_full_name', read_only=True)

    class Meta:
        model = Attendance
        fields = ['id', 'batch', 'student_profile', 'student_name', 'student_full_name', 'date', 'status']

class NoteSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = ['id', 'batch', 'title', 'description', 'file', 'file_url', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            return request.build_absolute_uri(obj.file.url)
        return None