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
    # This allows reading the nested user details
    user = UserSerializer(read_only=True)
    
    # These fields provide read-only, formatted data to the app
    institute = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    join_request_status = serializers.SerializerMethodField()
    fee_status = serializers.SerializerMethodField()
    preferred_topics = TopicSerializer(many=True, read_only=True)
    preferred_exams = ExamSerializer(many=True, read_only=True)

    # --- These fields are for WRITING data from the app to the backend ---
    
    # This handles the file upload
    profile_photo_upload = serializers.ImageField(source='profile_photo', write_only=True, required=False, allow_null=True)
    
    # These handle the many-to-many relationships by accepting a list of IDs
    preferred_topics_ids = serializers.PrimaryKeyRelatedField(
        queryset=Topic.objects.all(), source='preferred_topics', many=True, write_only=True, required=False
    )
    preferred_exams_ids = serializers.PrimaryKeyRelatedField(
        queryset=Exam.objects.all(), source='preferred_exams', many=True, write_only=True, required=False
    )

    class Meta:
        model = UserProfile
        # The `fields` list now correctly includes all readable and writable fields
        fields = [
            'id', 'user', 'institute', 'profile_photo', 'profile_photo_upload', 
            'qualifications', 'date_of_birth', 'place', 'preferred_difficulty',
            'is_owner', 'join_request_status', 'fee_status', 
            'preferred_topics', 'preferred_topics_ids',
            'preferred_exams', 'preferred_exams_ids','bio',
            'is_content_creator'
        ]
        # We make 'user' read-only in the Meta to prevent accidental updates via this serializer's main logic
        read_only_fields = ['user']

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
        
        # Handle nested User model update (first_name, last_name)
        user_data_str = self.context['request'].data.get('user')
        if user_data_str:
            try:
                user_data = json.loads(user_data_str)
                user_instance = instance.user
                user_serializer = UserSerializer(user_instance, data=user_data, partial=True)
                if user_serializer.is_valid(raise_exception=True):
                    user_serializer.save()
            except (json.JSONDecodeError, TypeError):
                # This handles cases where the data might not be a valid JSON string
                pass
            
        # The PrimaryKeyRelatedField and ImageField (with `source`) handle the updates
        # for preferred_exams, preferred_topics, and profile_photo automatically.
        
        # The super().update() handles all other standard UserProfile fields
        # like qualifications, place, etc.
        instance = super().update(instance, validated_data)
        
        instance.save()
        return instance



from rest_framework import serializers
from .models import Questions, DailyExam
import json
import csv
from io import StringIO
from django.core.exceptions import ValidationError

class QuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Questions
        fields = [
            'id', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d',
            'correct_answer', 'explanation'
        ]

class DailyExamSerializer(serializers.ModelSerializer):
    questions = QuestionsSerializer(many=True, read_only=True)
    class Meta:
        model = DailyExam
        fields = ['id', 'date', 'questions']

class TextUploadSerializer(serializers.Serializer):
    text_data = serializers.CharField(style={'base_template': 'textarea.html'})
    upload_type = serializers.ChoiceField(choices=[('questions', 'Questions'), ('daily_exam', 'Daily Exam')])
    format_type = serializers.ChoiceField(
        choices=[
            ('csv', 'CSV Format'),
            ('json', 'JSON Format'),
            ('simple', 'Simple Format')
        ],
        default='simple'
    )

class BulkUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=False)
    text_data = serializers.CharField(required=False, style={'base_template': 'textarea.html'})
    upload_type = serializers.ChoiceField(choices=[('questions', 'Questions'), ('daily_exam', 'Daily Exam')])
    format_type = serializers.ChoiceField(
        choices=[
            ('csv', 'CSV Format'),
            ('json', 'JSON Format'),
            ('simple', 'Simple Format')
        ],
        default='csv'
    )
    
    def validate(self, data):
        if not data.get('file') and not data.get('text_data'):
            raise serializers.ValidationError("Either file or text_data must be provided")
        
        if data.get('file') and data.get('text_data'):
            raise serializers.ValidationError("Provide either file or text_data, not both")
        
        if data.get('file'):
            if not data['file'].name.endswith(('.csv', '.xlsx', '.xls')):
                raise serializers.ValidationError("Only CSV and Excel files are supported")
        
        return data
    
from .models import DailyExamAttempt

# In questionbank/serializers.py

class DailyExamAttemptSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = DailyExamAttempt
        fields = ['id', 'user', 'score', 'time_taken', 'submitted_at']

class SubmitDailyExamSerializer(serializers.Serializer):
    answers = serializers.JSONField()
    time_taken = serializers.IntegerField(required=False, default=0)



# In questionbank/serializers.py
from .models import ModelExam, ModelExamAttempt

class ModelExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelExam
        fields = ['id', 'name', 'exam', 'duration_minutes']

class ModelExamDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    class Meta:
        model = ModelExam
        fields = ['id', 'name', 'exam', 'duration_minutes', 'questions']

class ModelExamAttemptSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = ModelExamAttempt
        fields = ['id', 'user', 'score', 'time_taken']


# In questionbank/serializers.py
from .models import PreviousYearPaper

class PreviousYearPaperSerializer(serializers.ModelSerializer):
    pdf_file_url = serializers.SerializerMethodField()

    class Meta:
        model = PreviousYearPaper
        fields = ['id', 'title', 'year', 'pdf_file_url']

    def get_pdf_file_url(self, obj):
        request = self.context.get('request')
        if obj.pdf_file and hasattr(obj.pdf_file, 'url'):
            return request.build_absolute_uri(obj.pdf_file.url)
        return None


# In questionbank/serializers.py
# In questionbank/serializers.py
from .models import Syllabus, ExamAnnouncement

class SyllabusSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    pdf_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Syllabus # Use the new model name
        fields = ['id', 'exam', 'exam_name', 'details', 'pdf_file_url']

    def get_pdf_file_url(self, obj):
        request = self.context.get('request')
        if obj.pdf_file and hasattr(obj.pdf_file, 'url'):
            return request.build_absolute_uri(obj.pdf_file.url)
        return None


class ExamAnnouncementSerializer(serializers.ModelSerializer):
    pdf_file_url = serializers.SerializerMethodField()

    class Meta:
        model = ExamAnnouncement
        fields = ['id', 'title', 'publication_date', 'pdf_file_url']

    def get_pdf_file_url(self, obj):
        request = self.context.get('request')
        if obj.pdf_file and hasattr(obj.pdf_file, 'url'):
            return request.build_absolute_uri(obj.pdf_file.url)
        return None