from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction

from .models import Institute, Message, FeeItem, Payment, InstituteJoinRequest, Batch, BatchMembership, Attendance, Note, InstituteMockTest, InstituteTestAttempt
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
            'login_bg_image', 'login_image_1', 'login_image_2', 'login_image_3',
            'show_leaderboard', 'allow_student_tests',
        ]
        read_only_fields = ['id']

# institutes/serializers.py

class StudentCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8, style={'input_type': 'password'})
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
    profile_photo = serializers.SerializerMethodField()
    phone_number = serializers.CharField(source='student_profile.phone_number', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = InstituteJoinRequest
        fields = ['id', 'user', 'full_name', 'phone_number', 'profile_photo', 'institute', 'status', 'requested_at']
        read_only_fields = ['id', 'user', 'full_name', 'phone_number', 'profile_photo', 'status', 'requested_at']

    def get_full_name(self, obj):
        if obj.student_profile and obj.student_profile.user:
            fn = f"{obj.student_profile.user.first_name} {obj.student_profile.user.last_name}".strip()
            return fn or obj.student_profile.user.username
        return ''

    def get_profile_photo(self, obj):
        if obj.student_profile and obj.student_profile.profile_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.student_profile.profile_photo.url)
            return obj.student_profile.profile_photo.url
        return None



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


class InstituteQuestionSerializer(serializers.Serializer):
    """Writable academy questions. The public QuestionSerializer is read-only presentation."""
    id = serializers.IntegerField(read_only=True)
    question_text = serializers.CharField()
    option_a = serializers.CharField()
    option_b = serializers.CharField()
    option_c = serializers.CharField()
    option_d = serializers.CharField()
    correct_answer = serializers.ChoiceField(choices=['A', 'B', 'C', 'D'])
    explanation = serializers.CharField(required=False, allow_blank=True, default='')
    difficulty = serializers.ChoiceField(choices=['easy', 'medium', 'hard'], default='medium')
    topic = serializers.IntegerField(required=False, allow_null=True)
    topic_name = serializers.CharField(read_only=True)

    def validate_topic(self, topic_id):
        from questionbank.models import Topic
        institute = self.context.get('institute')
        if not topic_id:
            if institute:
                topic, _ = Topic.objects.get_or_create(
                    institute=institute,
                    name="Academy Practice",
                    defaults={'slug': f"{institute.slug}-academy-practice"}
                )
                return topic
            return None
        topic = Topic.objects.filter(pk=topic_id, institute=institute).first()
        if not topic:
            topic = Topic.objects.filter(pk=topic_id).first()
            if not topic and institute:
                topic, _ = Topic.objects.get_or_create(
                    institute=institute,
                    name="Academy Practice",
                    defaults={'slug': f"{institute.slug}-academy-practice"}
                )
        return topic

    def _options(self, data):
        return {
            'A': data['option_a'].strip(),
            'B': data['option_b'].strip(),
            'C': data['option_c'].strip(),
            'D': data['option_d'].strip(),
        }

    def create(self, validated_data):
        from questionbank.models import Question, Topic
        institute = self.context.get('institute')
        topic = validated_data.pop('topic', None)
        if not topic and institute:
            topic, _ = Topic.objects.get_or_create(
                institute=institute,
                name="Academy Practice",
                defaults={'slug': f"{institute.slug}-academy-practice"}
            )
        question_text = validated_data.pop('question_text')
        options = self._options(validated_data)
        for key in ('option_a', 'option_b', 'option_c', 'option_d'):
            validated_data.pop(key, None)
        return Question.objects.create(
            text=question_text.strip(),
            options=options,
            correct_answer=validated_data['correct_answer'],
            explanation=validated_data.get('explanation') or '',
            difficulty=validated_data.get('difficulty') or 'medium',
            topic=topic,
            institute=institute,
        )

    def update(self, instance, validated_data):
        if 'topic' in validated_data and validated_data['topic']:
            instance.topic = validated_data['topic']
        if 'question_text' in validated_data:
            instance.text = validated_data['question_text'].strip()
        opts = dict(instance.options or {})
        for opt_key, field_name in (('A', 'option_a'), ('B', 'option_b'), ('C', 'option_c'), ('D', 'option_d')):
            if field_name in validated_data:
                opts[opt_key] = validated_data[field_name].strip()
        instance.options = opts
        if 'correct_answer' in validated_data:
            instance.correct_answer = validated_data['correct_answer']
        if 'explanation' in validated_data:
            instance.explanation = validated_data.get('explanation') or ''
        if 'difficulty' in validated_data:
            instance.difficulty = validated_data['difficulty']
        instance.save()
        return instance

    def to_representation(self, instance):
        opts = instance.options if isinstance(instance.options, dict) else {}
        return {
            'id': instance.id,
            'question_text': instance.text,
            'text': instance.text,
            'option_a': opts.get('A', ''),
            'option_b': opts.get('B', ''),
            'option_c': opts.get('C', ''),
            'option_d': opts.get('D', ''),
            'options': opts,
            'correct_answer': instance.correct_answer,
            'explanation': instance.explanation or '',
            'difficulty': instance.difficulty,
            'topic': instance.topic_id,
            'topic_name': instance.topic.name if instance.topic_id else '',
        }


class InstituteMockTestSerializer(serializers.ModelSerializer):
    batch_name = serializers.CharField(source='batch.name', read_only=True, default='')
    question_count = serializers.IntegerField(read_only=True)
    status = serializers.SerializerMethodField()
    total_attempts = serializers.SerializerMethodField()

    class Meta:
        model = InstituteMockTest
        fields = [
            'id', 'title', 'description', 'batch', 'batch_name',
            'duration_minutes', 'time_limit_per_question', 'can_repeat',
            'start_time', 'end_time', 'is_active', 'question_count',
            'status', 'total_attempts', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_status(self, obj):
        return obj.get_status()

    def get_total_attempts(self, obj):
        return obj.attempts.count()

    def create(self, validated_data):
        institute = self.context['institute']
        validated_data['institute'] = institute
        return super().create(validated_data)


class InstituteMockTestDetailSerializer(InstituteMockTestSerializer):
    questions_list = serializers.SerializerMethodField()

    class Meta(InstituteMockTestSerializer.Meta):
        fields = InstituteMockTestSerializer.Meta.fields + ['questions_list']

    def get_questions_list(self, obj):
        return [
            {
                'id': q.id,
                'question_text': q.text,
                'option_a': (q.options or {}).get('A', ''),
                'option_b': (q.options or {}).get('B', ''),
                'option_c': (q.options or {}).get('C', ''),
                'option_d': (q.options or {}).get('D', ''),
                'correct_answer': q.correct_answer,
                'explanation': q.explanation or '',
                'difficulty': q.difficulty,
                'topic_name': q.topic.name if q.topic else '',
            }
            for q in obj.questions.select_related('topic').all()
        ]
