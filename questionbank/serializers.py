from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import Sum

# --- Local application models ---
from .models import (
    ExamCategory, Exam, Topic, Question, Bookmark, Report, 
    UserProfile, UserAnswer, ExamSyllabus
)
# --- Cross-application models ---
from institutes.models import Institute

# ===================================================================
# --- Basic Model Serializers ---
# ===================================================================

class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ['id', 'name', 'year', 'duration_minutes']

class ExamCategorySerializer(serializers.ModelSerializer):
    exams = ExamSerializer(many=True, read_only=True)
    class Meta:
        model = ExamCategory
        fields = ['id', 'name', 'description', 'exams']

class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['id', 'name', 'institute', 'image']

class QuestionSerializer(serializers.ModelSerializer):
    # CORRECTED: This now includes all the new fields for a question
    exams = ExamSerializer(many=True, read_only=True)
    class Meta:
        model = Question
        fields = [
            'id', 'text', 'options', 'correct_answer', 'explanation', 
            'difficulty', 'institute', 'topic', 'sub_topic', 'exams'
        ]

class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ['id', 'question', 'created_at']

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'question', 'reason', 'created_at']

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']

class UserAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAnswer
        fields = ['question', 'selected_option']

class DetailedUserAnswerSerializer(serializers.ModelSerializer):
    """Provides full details about a user's answer for the history/review page."""
    question = QuestionSerializer(read_only=True)
    class Meta:
        model = UserAnswer
        fields = ['id', 'question', 'selected_option', 'is_correct', 'answered_at']


# ===================================================================
# --- Main UserProfile Serializer ---
# ===================================================================
# In questionbank/serializers.py
import json
# ... all other imports ...

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    institute = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    join_request_status = serializers.SerializerMethodField()
    fee_status = serializers.SerializerMethodField()
    preferred_topics = TopicSerializer(many=True, read_only=True)
    preferred_exams = ExamSerializer(many=True, read_only=True)

    # These fields are for WRITING data from the app to the backend
    profile_photo_upload = serializers.ImageField(source='profile_photo', write_only=True, required=False, allow_null=True)
    preferred_topics_ids = serializers.PrimaryKeyRelatedField(
        queryset=Topic.objects.all(), source='preferred_topics', many=True, write_only=True, required=False
    )
    preferred_exams_ids = serializers.PrimaryKeyRelatedField(
        queryset=Exam.objects.all(), source='preferred_exams', many=True, write_only=True, required=False
    )

    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'institute', 'profile_photo', 'profile_photo_upload',
            'qualifications', 'date_of_birth', 'place', 'preferred_difficulty',
            'is_owner', 'join_request_status', 'fee_status',
            'preferred_topics', 'preferred_topics_ids',
            'preferred_exams', 'preferred_exams_ids',
            'is_content_creator'
        ]

    def get_institute(self, obj):
        from institutes.serializers import InstituteSerializer
        if obj.institute:
            return InstituteSerializer(obj.institute, context=self.context).data
        return None

    def get_profile_photo(self, obj):
        if obj.profile_photo and hasattr(obj.profile_photo, 'url'):
            request = self.context.get('request')
            return request.build_absolute_uri(obj.profile_photo.url) if request else obj.profile_photo.url
        return None

    def get_is_owner(self, obj):
        return Institute.objects.filter(owner=obj.user).exists()

    def get_join_request_status(self, obj):
        # This requires the 'join_requests' related_name on the InstituteJoinRequest model
        if hasattr(obj, 'join_requests'):
            pending_request = obj.join_requests.filter(status='pending').first()
            if pending_request:
                return f"Request to join '{pending_request.institute.name}' is pending."
        return None

    def get_fee_status(self, obj):
        # This requires the 'fee_items' and 'payments' related_names on their respective models
        if hasattr(obj, 'fee_items') and hasattr(obj, 'payments'):
            total_dues = obj.fee_items.aggregate(total=Sum('amount'))['total'] or 0
            total_paid = obj.payments.aggregate(total=Sum('amount'))['total'] or 0
            balance = total_dues - total_paid
            return {'total_fees': total_dues, 'amount_paid': total_paid, 'balance_due': balance}
        return None
    
    def validate_preferred_exams_ids(self, value):
        if len(value) > 3:
            raise serializers.ValidationError("You can select a maximum of 3 preferred exams.")
        return value

    def update(self, instance, validated_data):
        # --- CORRECTED: This logic now properly handles nested user updates ---
        user_data_str = self.context['request'].data.get('user')
        if user_data_str:
            try:
                # If user data is sent as a stringified JSON (common with FormData), parse it
                user_data = json.loads(user_data_str)
                user_instance = instance.user
                
                # Update the user instance with the new data
                user_instance.first_name = user_data.get('first_name', user_instance.first_name)
                user_instance.last_name = user_data.get('last_name', user_instance.last_name)
                user_instance.save()
            except (json.JSONDecodeError, TypeError):
                # Handle cases where user data might not be a valid JSON string
                pass
            
        # The PrimaryKeyRelatedField handles preferred_exams and preferred_topics automatically
        
        # The super().update() handles all other standard UserProfile fields
        # like qualifications, place, and the profile_photo (via the `source` attribute).
        instance = super().update(instance, validated_data)
        
        instance.save()
        return instance