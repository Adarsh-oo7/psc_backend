from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import Sum

# --- Local application models ---
from .models import (
    Exam, Topic, Question, Bookmark, Report, 
    UserProfile, UserAnswer, ExamCategory
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
    class Meta:
        model = Question
        fields = ['id', 'text', 'options', 'correct_answer', 'explanation', 'difficulty', 'institute']

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


# In questionbank/serializers.py

class DetailedUserAnswerSerializer(serializers.ModelSerializer):
    """
    Provides full details about a user's answer, including the nested question.
    """
    question = QuestionSerializer(read_only=True)

    class Meta:
        model = UserAnswer
        fields = ['id', 'question', 'selected_option', 'is_correct', 'answered_at']

# ===================================================================
# --- Main UserProfile Serializer ---
# ===================================================================

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    institute = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    join_request_status = serializers.SerializerMethodField()
    fee_status = serializers.SerializerMethodField()
    preferred_topics = TopicSerializer(many=True, read_only=True)
    preferred_exams = ExamSerializer(many=True, read_only=True)

    profile_photo_upload = serializers.ImageField(write_only=True, required=False, allow_null=True)
    preferred_topics_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
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
            'preferred_exams', 'preferred_exams_ids'
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
        pending_request = obj.join_requests.filter(status='pending').first()
        if pending_request:
            return f"Request to join '{pending_request.institute.name}' is pending."
        return None

    def get_fee_status(self, obj):
        total_dues = obj.fee_items.aggregate(total=Sum('amount'))['total'] or 0
        total_paid = obj.payments.aggregate(total=Sum('amount'))['total'] or 0
        balance = total_dues - total_paid
        return {'total_fees': total_dues, 'amount_paid': total_paid, 'balance_due': balance}
    
    def validate_preferred_exams_ids(self, value):
        if len(value) > 3:
            raise serializers.ValidationError("You can select a maximum of 3 preferred exams.")
        return value

    def update(self, instance, validated_data):
        profile_photo_upload = validated_data.pop('profile_photo_upload', None)
        if profile_photo_upload:
            if instance.profile_photo:
                instance.profile_photo.delete(save=False)
            instance.profile_photo = profile_photo_upload
        
        preferred_topics_ids = validated_data.pop('preferred_topics_ids', None)
        
        # CORRECTED: The 'preferred_exams' field is handled automatically by the PrimaryKeyRelatedField
        # so we no longer need to manually handle it here.
        
        instance = super().update(instance, validated_data)
        
        if preferred_topics_ids is not None:
            instance.preferred_topics.set(preferred_topics_ids)
        
        instance.save()
        return instance