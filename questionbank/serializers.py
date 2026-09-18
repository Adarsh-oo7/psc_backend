from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import Sum

# --- Local application models ---
from .models import (
    ExamCategory, Exam, Topic, Question, Bookmark, Report, 
    UserProfile, UserAnswer, ExamSyllabus, CurrentAffairs,
    MasterStudyPlan, UserExamProgress
)
# --- Cross-application models ---
from institutes.models import Institute

# ===================================================================
# --- Basic Model Serializers ---
# ===================================================================

class ExamSerializer(serializers.ModelSerializer):
    exam_dates = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            'id', 'name', 'slug', 'year', 'duration_minutes', 'category_number',
            'expected_exam_date', 'exam_dates', 'official_syllabus', 'question_pattern',
        ]

    def get_exam_dates(self, obj):
        from .syllabus_db import SYLLABUS_DATABASE, resolve_exam_slug
        slug_key = resolve_exam_slug(obj.slug or obj.name)
        data = SYLLABUS_DATABASE.get(slug_key) or {}
        return data.get('exam_dates') or None

class ExamCategorySerializer(serializers.ModelSerializer):
    exams = ExamSerializer(many=True, read_only=True)
    class Meta:
        model = ExamCategory
        fields = ['id', 'name', 'description', 'exams']

class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['id', 'name', 'institute', 'image']


class AttemptCountListSerializer(serializers.ListSerializer):
    """Prefetch per-question attempt counts so option shuffle stays stable in a list."""

    def to_representation(self, data):
        request = self.context.get('request')
        shuffle_on = self.context.get('shuffle')
        if shuffle_on is None:
            shuffle_on = True
        if (
            shuffle_on
            and request is not None
            and getattr(getattr(request, 'user', None), 'is_authenticated', False)
            and 'attempt_counts' not in self.context
        ):
            items = list(data)
            ids = [getattr(q, 'id', None) for q in items if getattr(q, 'id', None)]
            if ids:
                from django.db.models import Count
                self.context['attempt_counts'] = dict(
                    UserAnswer.objects.filter(user=request.user, question_id__in=ids)
                    .values('question_id')
                    .annotate(c=Count('id'))
                    .values_list('question_id', 'c')
                )
            return super().to_representation(items)
        return super().to_representation(data)


def presented_question_fields(obj, context):
    from .kpsc_format import present_mcq
    request = context.get('request')
    user = getattr(request, 'user', None) if request is not None else None
    authenticated = user is not None and getattr(user, 'is_authenticated', False)
    shuffle = context.get('shuffle')
    if shuffle is None:
        shuffle = authenticated
    user_id = 0
    salt = 0
    qid = getattr(obj, 'id', 0) or 0
    if shuffle and authenticated:
        user_id = user.id
        counts = context.get('attempt_counts')
        if isinstance(counts, dict):
            salt = int(counts.get(qid, 0) or 0)
        else:
            salt = UserAnswer.objects.filter(user=user, question_id=qid).count()
    return present_mcq(
        obj.text,
        obj.options,
        obj.correct_answer,
        getattr(obj, 'explanation', '') or '',
        user_id=user_id,
        question_id=qid,
        salt=salt,
        shuffle=bool(shuffle),
    )


class QuestionSerializer(serializers.ModelSerializer):
    exams = ExamSerializer(many=True, read_only=True)
    topic = TopicSerializer(read_only=True)
    options = serializers.SerializerMethodField()
    correct_answer = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            'id', 'text', 'options', 'correct_answer', 'explanation', 
            'difficulty', 'institute', 'topic', 'sub_topic', 'exams'
        ]
        list_serializer_class = AttemptCountListSerializer

    def _presented(self, obj):
        cache = getattr(self, '_presented_cache', None)
        if cache is None:
            self._presented_cache = {}
            cache = self._presented_cache
        key = getattr(obj, 'id', None) or id(obj)
        if key not in cache:
            cache[key] = presented_question_fields(obj, self.context)
        return cache[key]

    def get_text(self, obj):
        return self._presented(obj)['text']

    def get_options(self, obj):
        return self._presented(obj)['options']

    def get_correct_answer(self, obj):
        return self._presented(obj)['correct_answer']

class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ['id', 'question', 'created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        ctx = {**self.context, 'shuffle': False}
        data['question'] = QuestionSerializer(instance.question, context=ctx).data
        return data

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'question', 'report_type', 'reason', 'created_at']
        read_only_fields = ['id', 'created_at']

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']

class UserAnswerSerializer(serializers.ModelSerializer):
    selected_option = serializers.CharField(max_length=1, required=False, allow_blank=True, default='')

    class Meta:
        model = UserAnswer
        fields = ['question', 'selected_option']

class DetailedUserAnswerSerializer(serializers.ModelSerializer):
    """Provides full details about a user's answer for the history/review page."""
    question = serializers.SerializerMethodField()

    class Meta:
        model = UserAnswer
        fields = ['id', 'question', 'selected_option', 'is_correct', 'answered_at']

    def get_question(self, obj):
        ctx = {**self.context, 'shuffle': False}
        return QuestionSerializer(obj.question, context=ctx).data


# ===================================================================
# --- Main UserProfile Serializer ---
# ===================================================================
# In questionbank/serializers.py
import json
# ... all other imports ...

class UserProfileSerializer(serializers.ModelSerializer):
    # This allows reading the nested user details
    user = UserSerializer(read_only=True)
    district_display = serializers.SerializerMethodField(read_only=True)
    
    # These fields provide read-only, formatted data to the app
    institute = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    join_request_status = serializers.SerializerMethodField()
    fee_status = serializers.SerializerMethodField()
    preferred_topics = TopicSerializer(many=True, read_only=True)
    preferred_exams = ExamSerializer(many=True, read_only=True)
    primary_exam_detail = ExamSerializer(source='primary_exam', read_only=True)
    primary_exam_id = serializers.PrimaryKeyRelatedField(
        queryset=Exam.objects.all(), source='primary_exam', write_only=True, required=False, allow_null=True
    )

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
        fields = [
            'id', 'user', 'phone_number', 'institute', 'profile_photo', 'profile_photo_upload', 
            'qualifications', 'date_of_birth', 'place', 'district', 'district_display', 'preferred_difficulty',
            'preferred_language', 'is_owner', 'join_request_status', 'fee_status', 
            'preferred_topics', 'preferred_topics_ids',

            'preferred_exams', 'preferred_exams_ids', 'primary_exam_detail', 'primary_exam_id', 'bio',
            'is_content_creator', 'total_xp', 'level', 'current_streak', 
            'longest_streak', 'last_active_date', 'streak_freeze_count'
        ]
        read_only_fields = ['user', 'total_xp', 'level', 'current_streak', 'longest_streak', 'last_active_date', 'streak_freeze_count']

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

    def get_district_display(self, obj):
        return obj.get_district_display() if obj.district else ''

    def to_representation(self, instance):
        from questionbank.gamification import refresh_streak
        refresh_streak(instance)
        return super().to_representation(instance)

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
from .models import Question, DailyExam
import json
import csv
from io import StringIO
from django.core.exceptions import ValidationError

class QuestionsSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()
    correct_answer = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            'id', 'text', 'options', 'correct_answer', 'explanation', 'difficulty'
        ]
        list_serializer_class = AttemptCountListSerializer

    def _presented(self, obj):
        cache = getattr(self, '_presented_cache', None)
        if cache is None:
            self._presented_cache = {}
            cache = self._presented_cache
        key = getattr(obj, 'id', None) or id(obj)
        if key not in cache:
            cache[key] = presented_question_fields(obj, self.context)
        return cache[key]

    def get_text(self, obj):
        return self._presented(obj)['text']

    def get_options(self, obj):
        return self._presented(obj)['options']

    def get_correct_answer(self, obj):
        return self._presented(obj)['correct_answer']

class DailyExamSerializer(serializers.ModelSerializer):
    questions = QuestionsSerializer(many=True, read_only=True)
    class Meta:
        model = DailyExam
        fields = ['id', 'date', 'questions']

    def to_representation(self, instance):
        self.context['shuffle'] = False
        return super().to_representation(instance)

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

    def to_representation(self, instance):
        self.context['shuffle'] = False
        return super().to_representation(instance)

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


def get_consolidated_subject(topic_name):
    name = topic_name.lower()
    if any(x in name for x in ['malayalam', 'regional language', 'tamil', 'kannada']):
        return "Regional Language (Malayalam/Kannada/Tamil)"
    if any(x in name for x in ['english', 'grammar', 'tense', 'voice', 'speech', 'synonym', 'antonym', 'vocabulary', 'spelling', 'comprehension']):
        return "General English"
    if any(x in name for x in ['arithmetic', 'math', 'mental', 'reasoning', 'hcf', 'lcm', 'bodmas', 'fraction', 'ratio', 'proportion', 'interest', 'average', 'algebra', 'geometry', 'mensuration', 'data interpretation', 'simplification', 'profit', 'loss', 'time & work', 'speed', 'distance', 'mixture', 'logical']):
        return "Simple Arithmetic & Mental Ability"
    if any(x in name for x in ['current affairs', 'news', 'events', 'awards', 'sports', 'games', 'observances', 'in news']):
        return "Current Affairs"
    return "General Knowledge & Renaissance"

# In questionbank/serializers.py
# In questionbank/serializers.py
from .models import Syllabus, ExamAnnouncement

class SyllabusSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    pdf_file_url = serializers.SerializerMethodField()
    subject_weights = serializers.SerializerMethodField()

    class Meta:
        model = Syllabus # Use the new model name
        fields = ['id', 'exam', 'exam_name', 'details', 'pdf_file_url', 'subject_weights']

    def get_pdf_file_url(self, obj):
        request = self.context.get('request')
        if obj.pdf_file and hasattr(obj.pdf_file, 'url'):
            return request.build_absolute_uri(obj.pdf_file.url)
        return None

    def get_subject_weights(self, obj):
        name_lower = obj.exam.name.lower()
        if 'ldc' in name_lower or 'clerk' in name_lower:
            return [
                {"subject": "Part I: General Knowledge", "weight": 50.0},
                {"subject": "Part II: Current Affairs", "weight": 20.0},
                {"subject": "Part III: Simple Arithmetic & Mental Ability", "weight": 10.0},
                {"subject": "Part IV: General English", "weight": 10.0},
                {"subject": "Part V: Regional Language", "weight": 10.0}
            ]
        elif 'lgs' in name_lower or 'servant' in name_lower:
            return [
                {"subject": "Part I: General Knowledge", "weight": 40.0},
                {"subject": "Part II: Current Affairs", "weight": 20.0},
                {"subject": "Part III: Science", "weight": 10.0},
                {"subject": "Part IV: Public Health", "weight": 10.0},
                {"subject": "Part V: Simple Arithmetic & Mental Ability", "weight": 20.0}
            ]
        elif 'sub inspector' in name_lower or 'si ' in name_lower or 'si(' in name_lower or 'inspector' in name_lower:
            return [
                {"subject": "General Knowledge & Current Affairs", "weight": 50.0},
                {"subject": "General Science", "weight": 10.0},
                {"subject": "Mental Ability & Logical Reasoning", "weight": 10.0},
                {"subject": "Quantitative Aptitude", "weight": 10.0},
                {"subject": "General English", "weight": 10.0},
                {"subject": "Regional Language (Malayalam/Kannada/Tamil)", "weight": 5.0},
                {"subject": "Police & Legal Subjects", "weight": 5.0}
            ]
        elif 'constable' in name_lower or 'cpo' in name_lower or 'police' in name_lower:
            return [
                {"subject": "Part I: General Knowledge", "weight": 40.0},
                {"subject": "Part II: Current Affairs", "weight": 10.0},
                {"subject": "Part III: Simple Arithmetic & Mental Ability", "weight": 10.0},
                {"subject": "Part IV: General English", "weight": 10.0},
                {"subject": "Part V: Regional Language", "weight": 10.0},
                {"subject": "Part VI: Special Topics (Job-Related)", "weight": 20.0}
            ]
        elif 'forest' in name_lower or 'beat forest' in name_lower:
            return [
                {"subject": "General Knowledge", "weight": 40.0},
                {"subject": "Current Affairs", "weight": 10.0},
                {"subject": "Simple Arithmetic, Mental Ability & Reasoning", "weight": 10.0},
                {"subject": "General English", "weight": 10.0},
                {"subject": "Regional Language (Malayalam/Kannada/Tamil)", "weight": 10.0},
                {"subject": "Special Topics (Forest & Wildlife)", "weight": 20.0}
            ]
        elif 'degree' in name_lower or 'graduate' in name_lower:
            return [
                {"subject": "Part I: General Knowledge", "weight": 50.0},
                {"subject": "Part II: Simple Arithmetic & Mental Ability", "weight": 20.0},
                {"subject": "Part III: General English", "weight": 20.0},
                {"subject": "Part IV: Regional Language", "weight": 10.0}
            ]

        # Consolidated DB-driven fallback for custom exams
        parts = obj.exam.syllabus_parts.all()
        if not parts.exists():
            return []
        total_qs = sum(p.num_questions for p in parts)
        if total_qs == 0:
            return []
            
        consolidated = {}
        for p in parts:
            subject = get_consolidated_subject(p.topic.name)
            consolidated[subject] = consolidated.get(subject, 0) + p.num_questions
            
        order = [
            "General Knowledge & Renaissance",
            "Current Affairs",
            "Simple Arithmetic & Mental Ability",
            "General English",
            "Regional Language (Malayalam/Kannada/Tamil)"
        ]
        
        result = []
        for subject in order:
            if subject in consolidated:
                result.append({
                    "subject": subject,
                    "weight": round((consolidated[subject] / total_qs) * 100, 1)
                })
        for subject, count in consolidated.items():
            if not any(r['subject'] == subject for r in result):
                result.append({
                    "subject": subject,
                    "weight": round((count / total_qs) * 100, 1)
                })
        return result


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


class CurrentAffairsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrentAffairs
        fields = ['id', 'title', 'slug', 'content', 'category', 'publication_date',
                  'psc_likelihood', 'ai_summary', 'source_url', 'mcq', 'created_at']


from .models import StudyFeedCard

class StudyFeedCardSerializer(serializers.ModelSerializer):
    content_data = serializers.SerializerMethodField()

    class Meta:
        model = StudyFeedCard
        fields = ['id', 'card_type', 'title', 'content_data', 'psc_likelihood_tag', 'created_at']

    def get_content_data(self, obj):
        from .kpsc_format import format_question_payload, present_mcq
        data = obj.content_data if isinstance(obj.content_data, dict) else {}
        if obj.card_type != 'question':
            return data
        text = data.get('question_text') or data.get('text') or ''
        question_id = data.get('question_id') or 0
        payload = format_question_payload(
            text,
            data.get('options') or {},
            data.get('correct_answer'),
            data.get('explanation') or '',
            extra={'question_id': question_id},
        )
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request is not None else None
        user_id = 0
        salt = 0
        if user is not None and getattr(user, 'is_authenticated', False):
            user_id = user.id
            if question_id:
                salt = UserAnswer.objects.filter(user=user, question_id=question_id).count()
        presented = present_mcq(
            payload['text'],
            payload['options'],
            payload['correct_answer'],
            payload['explanation'],
            user_id=user_id,
            question_id=int(question_id or 0),
            salt=salt,
            shuffle=True,
            extra={'question_id': question_id},
        )
        presented['question_text'] = presented['text']
        return presented


# ===================================================================
# --- Study Flow & Analytics Serializers ---
# ===================================================================
from .models import TopicProgress, PracticeSession, SessionAnswer

class TopicListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    user_accuracy = serializers.SerializerMethodField()
    is_weak_area = serializers.SerializerMethodField()
    last_practiced = serializers.SerializerMethodField()
    section_key = serializers.SerializerMethodField()
    section_title = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            'id', 'name', 'slug', 'image', 'question_count',
            'user_accuracy', 'is_weak_area', 'last_practiced',
            'section_key', 'section_title',
        ]

    def get_section_key(self, obj):
        from .psc_sections import classify_topic
        return classify_topic(obj.name)

    def get_section_title(self, obj):
        from .psc_sections import classify_label, classify_topic
        return classify_label(classify_topic(obj.name))

    def get_question_count(self, obj):
        return obj.questions_topic.count()

    def _get_progress(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return None
        if not hasattr(self, '_progress_cache'):
            self._progress_cache = {
                tp.topic_id: tp for tp in TopicProgress.objects.filter(user=request.user)
            }
        return self._progress_cache.get(obj.id)

    def get_user_accuracy(self, obj):
        progress = self._get_progress(obj)
        return progress.accuracy if progress else 0.0

    def get_is_weak_area(self, obj):
        progress = self._get_progress(obj)
        return progress.is_weak_area if progress else False

    def get_last_practiced(self, obj):
        progress = self._get_progress(obj)
        return progress.last_practiced if progress else None


class QuestionMockSerializer(serializers.ModelSerializer):
    topic = serializers.CharField(source='topic.name', read_only=True)
    options = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'text', 'options', 'difficulty', 'sub_topic', 'topic']

    def get_options(self, obj):
        from .kpsc_format import normalize_options
        return normalize_options(obj.options)

    def get_text(self, obj):
        from .kpsc_format import clean_question_text
        return clean_question_text(obj.text)


class QuestionResultSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()
    correct_answer = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'text', 'options', 'correct_answer', 'explanation', 'difficulty']
        list_serializer_class = AttemptCountListSerializer

    def _presented(self, obj):
        cache = getattr(self, '_presented_cache', None)
        if cache is None:
            self._presented_cache = {}
            cache = self._presented_cache
        key = getattr(obj, 'id', None) or id(obj)
        if key not in cache:
            cache[key] = presented_question_fields(obj, self.context)
        return cache[key]

    def get_options(self, obj):
        return self._presented(obj)['options']

    def get_correct_answer(self, obj):
        return self._presented(obj)['correct_answer']

    def get_text(self, obj):
        return self._presented(obj)['text']


class PracticeSessionSerializer(serializers.ModelSerializer):
    topic = serializers.CharField(source='topic.name', read_only=True)
    score_percent = serializers.FloatField(read_only=True)

    class Meta:
        model = PracticeSession
        fields = [
            'id', 'session_type', 'topic', 'difficulty', 'total_questions',
            'correct_count', 'score_percent', 'started_at', 'completed_at',
            'time_taken_secs'
        ]


class SessionAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option = serializers.CharField(max_length=1, required=False, allow_blank=True, default='')
    time_spent_secs = serializers.IntegerField(required=False, default=0)


# Keep other serializers needed for previous APIs
class PYQDetailSerializer(serializers.ModelSerializer):
    pdf_file_url = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = PreviousYearPaper
        fields = ['id', 'title', 'year', 'pdf_file_url', 'questions', 'question_count']

    def get_pdf_file_url(self, obj):
        request = self.context.get('request')
        if obj.pdf_file and hasattr(obj.pdf_file, 'url'):
            return request.build_absolute_uri(obj.pdf_file.url) if request else obj.pdf_file.url
        return None

    def get_questions(self, obj):
        ctx = {**self.context, 'shuffle': False}
        return QuestionSerializer(obj.questions.all(), many=True, context=ctx).data

    def get_question_count(self, obj):
        return obj.questions.count()


class QuestionSubmissionSerializer(serializers.Serializer):
    question_text = serializers.CharField(min_length=10)
    option_a = serializers.CharField()
    option_b = serializers.CharField()
    option_c = serializers.CharField()
    option_d = serializers.CharField()
    correct_answer = serializers.ChoiceField(choices=['A', 'B', 'C', 'D'])
    topic_id = serializers.IntegerField()
    exam_id = serializers.IntegerField(required=False, allow_null=True)
    explanation = serializers.CharField(required=False, allow_blank=True, default='')
    language = serializers.ChoiceField(choices=['en', 'ml'], default='en')

    def validate(self, attrs):
        import re
        import hashlib
        
        question_text = attrs.get('question_text')
        options_dict = {
            'A': attrs.get('option_a'),
            'B': attrs.get('option_b'),
            'C': attrs.get('option_c'),
            'D': attrs.get('option_d')
        }
        
        normalized = re.sub(r'[^\w\s]', '', question_text).lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        
        if options_dict:
            opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(options_dict.items()))
            normalized = f"{normalized}||{opts_str}"
            
        text_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        if Question.objects.filter(text_hash=text_hash).exists():
            raise serializers.ValidationError({"question_text": "This question already exists"})
            
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None

        # Map options
        options_dict = {
            'A': validated_data['option_a'],
            'B': validated_data['option_b'],
            'C': validated_data['option_c'],
            'D': validated_data['option_d']
        }

        topic = Topic.objects.get(id=validated_data['topic_id'])
        
        q = Question.objects.create(
            text=validated_data['question_text'],
            options=options_dict,
            correct_answer=validated_data['correct_answer'],
            topic=topic,
            explanation=validated_data.get('explanation', ''),
            language=validated_data.get('language', 'en'),
            status='pending',
            source='community',
            submitted_by=user
        )

        exam_id = validated_data.get('exam_id')
        if exam_id:
            try:
                exam = Exam.objects.get(id=exam_id)
                q.exams.add(exam)
            except Exam.DoesNotExist:
                pass

        return q


class UserSubmissionSerializer(serializers.ModelSerializer):
    option_a = serializers.SerializerMethodField()
    option_b = serializers.SerializerMethodField()
    option_c = serializers.SerializerMethodField()
    option_d = serializers.SerializerMethodField()
    topic_name = serializers.CharField(source='topic.name', read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'text', 'option_a', 'option_b', 'option_c', 'option_d',
            'correct_answer', 'topic_name', 'explanation', 'language', 'status'
        ]

    def get_option_a(self, obj):
        return obj.options.get('A', '')
    def get_option_b(self, obj):
        return obj.options.get('B', '')
    def get_option_c(self, obj):
        return obj.options.get('C', '')
    def get_option_d(self, obj):
        return obj.options.get('D', '')


class MasterStudyPlanSerializer(serializers.ModelSerializer):
    exam_name = serializers.SerializerMethodField()
    exam_id = serializers.SerializerMethodField()
    official_syllabus = serializers.SerializerMethodField()
    question_pattern = serializers.SerializerMethodField()

    class Meta:
        model = MasterStudyPlan
        fields = [
            'id', 'exam_id', 'exam_name', 'title', 'description', 
            'estimated_days', 'syllabus_structure', 'weekly_milestones', 
            'mock_test_schedule', 'revision_schedule', 'pyq_schedule', 
            'official_syllabus', 'question_pattern', 'updated_at'
        ]

    def get_exam_name(self, obj):
        return obj.exam.name if obj.exam else ""

    def get_exam_id(self, obj):
        return obj.exam.id if obj.exam else None

    def get_official_syllabus(self, obj):
        return getattr(obj.exam, 'official_syllabus', {}) if obj.exam else {}

    def get_question_pattern(self, obj):
        return getattr(obj.exam, 'question_pattern', {}) if obj.exam else {}


class UserExamProgressSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    current_topic_name = serializers.CharField(source='current_topic.name', read_only=True)

    class Meta:
        model = UserExamProgress
        fields = [
            'id', 'user', 'exam', 'exam_name', 'completed_topic_ids', 
            'completed_mock_ids', 'completed_pyq_ids', 'current_topic', 
            'current_topic_name', 'last_studied'
        ]
        read_only_fields = ['user', 'last_studied']




