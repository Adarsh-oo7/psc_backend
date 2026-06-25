# --- Imports ---
from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Case, When, FloatField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from random import choice, shuffle
import logging

# Google OAuth & SimpleJWT Imports
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

# Local application imports
from .models import (
    Exam, Topic, Question, Bookmark, Report, UserProfile, 
    UserAnswer, ExamCategory, ExamSyllabus, UserFeedView
)
from .serializers import (
    ExamSerializer, TopicSerializer, QuestionSerializer, QuestionMockSerializer,
    BookmarkSerializer, ReportSerializer, UserSerializer, 
    UserProfileSerializer, UserAnswerSerializer, ExamCategorySerializer,
    QuestionSubmissionSerializer, UserSubmissionSerializer
)

# Cross-application imports
from institutes.models import Message, InstituteJoinRequest
from institutes.serializers import ReceivedMessageSerializer, JoinRequestSerializer

# Setup
logger = logging.getLogger(__name__)
User = get_user_model()


# ===================================================================
# --- AUTHENTICATION & PROFILE VIEWS ---
# ===================================================================

class RegisterView(generics.CreateAPIView):
    """Handles new user registration for the general public."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        if not all([username, email, password]):
            return Response({'error': 'Username, email, and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.create_user(
            username=username, 
            email=email, 
            password=password,
            first_name=request.data.get('first_name', ''),
            last_name=request.data.get('last_name', '')
        )
        UserProfile.objects.create(user=user)
        logger.info(f"User {username} registered successfully.")
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

class UserView(generics.RetrieveAPIView):
    """Retrieves details for the currently authenticated user."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    def get_object(self):
        return self.request.user

class UserProfileView(generics.RetrieveUpdateAPIView):
    """Retrieves and updates the profile for the authenticated user."""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class GoogleSignInView(views.APIView):
    """Handles Google OAuth2 Sign-In and creates/logs in users."""
    permission_classes = [AllowAny]

    def post(self, request):
        credential = request.data.get('credential')
        if not credential:
            return Response({'error': 'Credential token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
        if not client_id:
            logger.error("GOOGLE_CLIENT_ID is not configured in Django settings.")
            return Response({'error': 'Google Sign-In is not configured on the server.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            # Verify Google ID Token
            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                client_id
            )

            # Check issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                return Response({'error': 'Invalid token issuer.'}, status=status.HTTP_400_BAD_REQUEST)

            email = idinfo.get('email')
            if not email:
                return Response({'error': 'Email not provided by Google.'}, status=status.HTTP_400_BAD_REQUEST)

            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')

            # Check if user exists by email
            user = User.objects.filter(email=email).first()
            if not user:
                # Generate a unique username based on email
                username_base = email.split('@')[0]
                username = username_base
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{username_base}{counter}"
                    counter += 1

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name
                )
                user.set_unusable_password()
                user.save()

            # Ensure profile exists
            profile, _ = UserProfile.objects.get_or_create(user=user)

            # Generate SimpleJWT tokens
            refresh = RefreshToken.for_user(user)
            has_preferred_exams = profile.preferred_exams.exists()

            logger.info(f"User {user.username} authenticated successfully via Google Sign-In.")

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'has_preferred_exams': has_preferred_exams,
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.warning(f"Invalid Google ID token signature or claim: {str(e)}")
            return Response({
                'error': 'Invalid Google token.',
                'details': {
                    'server_client_id': client_id,
                    'token_preview': f"{credential[:15]}...{credential[-15:]}" if credential else None
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            logger.exception("Unexpected error during Google Sign-In.")
            return Response({
                'error': 'Internal server error.',
                'exception_type': type(e).__name__,
                'exception_message': str(e),
                'traceback': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===================================================================
# --- PUBLIC & TENANT-AWARE CONTENT VIEWS ---
# ===================================================================

class ExamListView(generics.ListAPIView):
    """Lists all exam categories, with the exams nested under each category."""
    queryset = ExamCategory.objects.prefetch_related('exams').all().order_by('order')
    serializer_class = ExamCategorySerializer
    permission_classes = [AllowAny]

class TopicListView(generics.ListAPIView):
    """Lists topics available to the user (global + their institute's)."""
    serializer_class = TopicSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        user = self.request.user
        base_query = Q(institute__isnull=True)
        if user.is_authenticated and hasattr(user, 'userprofile') and user.userprofile.institute:
            base_query |= Q(institute=user.userprofile.institute)
            
        preferred_exams = Exam.objects.none()
        if user and user.is_authenticated and hasattr(user, 'userprofile'):
            user_prefs = user.userprofile.preferred_exams.all()
            if user_prefs.exists():
                q_obj = Q()
                for exam in user_prefs:
                    q_obj |= Q(id=exam.id)
                    words = [w for w in exam.name.replace('(', '').replace(')', '').replace('/', ' ').split() if len(w) > 2]
                    if words:
                        sub_q = Q()
                        for word in words:
                            sub_q |= Q(name__icontains=word)
                        q_obj |= sub_q
                preferred_exams = Exam.objects.filter(q_obj).distinct()

        if preferred_exams.exists():
            syllabus_topics = Topic.objects.filter(examsyllabus__exam__in=preferred_exams).distinct()
            if syllabus_topics.exists():
                base_query &= Q(id__in=syllabus_topics)
                
        return Topic.objects.filter(base_query).distinct().order_by('name')

# In questionbank/views.py

class QuestionListView(generics.ListAPIView):
    """
    Lists questions available to the user.
    - Can be filtered by `exam_id` or `topic_id` or `difficulty`.
    - Integrates with QuestionEngine to provide personalized anti-repetition.
    """
    serializer_class = QuestionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user = self.request.user
        filters = {}

        exam_id = self.request.query_params.get('exam_id')
        if exam_id:
            filters['exam_id'] = exam_id

        topic_id = self.request.query_params.get('topic_id')
        if topic_id:
            filters['topic_id'] = topic_id

        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            filters['difficulty'] = difficulty

        limit = self.request.query_params.get('limit')
        limit_val = int(limit) if limit and limit.isdigit() else None

        from .engine import QuestionEngine
        return QuestionEngine.get_questions_for_user(user, filters, limit_val)


class DailyQuestionView(views.APIView):
    """Provides a single random personalized question for a daily quiz using the engine."""
    permission_classes = [AllowAny]
    def get(self, request):
        user = request.user
        from .engine import QuestionEngine
        qs = QuestionEngine.get_daily_quiz(user, limit=1)
        if not qs.exists():
            return Response({'error': 'No questions available'}, status=status.HTTP_404_NOT_FOUND)
        question = qs.first()
        return Response(QuestionSerializer(question, context={'request': request}).data)


class DailyQuizView(views.APIView):
    """Provides today's daily quiz questions — unique per user per day."""
    permission_classes = [AllowAny]
    def get(self, request):
        user = request.user
        limit = request.query_params.get('limit', '10')
        limit_val = int(limit) if limit and limit.isdigit() else 10
        from .engine import QuestionEngine
        qs = QuestionEngine.get_daily_quiz(user, limit=limit_val)
        serializer = QuestionSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class WeakAreaQuestionsView(generics.ListAPIView):
    """Lists questions from topics where user accuracy is below 50%."""
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        limit = self.request.query_params.get('limit', '20')
        limit_val = int(limit) if limit and limit.isdigit() else 20
        from .engine import QuestionEngine
        return QuestionEngine.get_weak_area_questions(user, limit=limit_val)


# ===================================================================
# --- MOCK EXAM & PROGRESS VIEWS ---
# ===================================================================

class GenerateMockExamView(views.APIView):
    """Generates a full mock exam based on the ExamSyllabus, padded to exactly 100 questions."""
    permission_classes = [IsAuthenticated]
    def get(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
        syllabus_parts = exam.syllabus_parts.all()
        
        # Find similar exams if direct syllabus doesn't exist
        words = [w for w in exam.name.replace('(', '').replace(')', '').replace('/', ' ').split() if len(w) > 2]
        similar_exams = Exam.objects.filter(id=exam.id)
        if words:
            q_obj = Q()
            for word in words:
                q_obj |= Q(name__icontains=word)
            similar_exams = Exam.objects.filter(q_obj)

        if not syllabus_parts.exists():
            syllabus_parts = ExamSyllabus.objects.filter(exam__in=similar_exams)
            
        topic_num_questions = {}
        for part in syllabus_parts:
            topic_num_questions[part.topic_id] = max(
                topic_num_questions.get(part.topic_id, 0),
                part.num_questions
            )
            
        all_questions = []
        seen_ids = set()
        
        # 1. Primary: Load questions according to syllabus topic weightage
        for topic_id, num_qs in topic_num_questions.items():
            if num_qs <= 0:
                continue
            questions = list(Question.objects.filter(topic_id=topic_id).order_by('?')[:num_qs])
            for q in questions:
                if q.id not in seen_ids:
                    all_questions.append(q)
                    seen_ids.add(q.id)
                    
        # 2. Pad to exactly 100 if we have a deficit
        # Level 1 padding: Get more questions from the syllabus topics
        if len(all_questions) < 100:
            topic_ids = list(topic_num_questions.keys())
            if topic_ids:
                additional_qs = list(Question.objects.filter(topic_id__in=topic_ids).exclude(id__in=seen_ids).order_by('?')[:100 - len(all_questions)])
                for q in additional_qs:
                    if q.id not in seen_ids:
                        all_questions.append(q)
                        seen_ids.add(q.id)
                        
        # Level 2 padding: Get questions associated with this exam or similar exams
        if len(all_questions) < 100:
            exam_qs = list(Question.objects.filter(exams__in=similar_exams).exclude(id__in=seen_ids).order_by('?')[:100 - len(all_questions)])
            for q in exam_qs:
                if q.id not in seen_ids:
                    all_questions.append(q)
                    seen_ids.add(q.id)
                    
        # Level 3 padding: Get any general/active questions in the database
        if len(all_questions) < 100:
            any_qs = list(Question.objects.exclude(id__in=seen_ids).order_by('?')[:100 - len(all_questions)])
            for q in any_qs:
                if q.id not in seen_ids:
                    all_questions.append(q)
                    seen_ids.add(q.id)
                    
        # If we somehow exceeded 100 questions (due to weightage sum), slice it down
        if len(all_questions) > 100:
            all_questions = all_questions[:100]
            
        shuffle(all_questions)
        response_data = {
            'exam_name': exam.name, 'duration_minutes': exam.duration_minutes,
            'questions': QuestionMockSerializer(all_questions, many=True).data
        }
        return Response(response_data)

class SubmitAnswerView(generics.CreateAPIView):
    """Saves a user's single answer during a simple practice quiz."""
    serializer_class = UserAnswerSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        question = serializer.validated_data['question']
        selected_option = serializer.validated_data['selected_option']
        is_correct = (selected_option == question.correct_answer)
        
        serializer.save(user=request.user, is_correct=is_correct)
        
        # Award XP and update streak
        from questionbank.gamification import award_xp, update_streak
        xp_earned = 10 if is_correct else 2
        _, level_up, new_level = award_xp(request.user, xp_earned)
        current_streak, longest_streak, freeze_used, streak_promo_awarded = update_streak(request.user)
        
        response_data = serializer.data
        response_data['gamification'] = {
            'xp_earned': xp_earned,
            'level_up': level_up,
            'new_level': new_level,
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'freeze_used': freeze_used,
            'streak_promo_awarded': streak_promo_awarded
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


# In questionbank/views.py
# In questionbank/views.py

# In questionbank/views.py

class SubmitExamView(views.APIView):
    """Receives and processes all answers for a completed mock exam."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        answers_data = request.data.get('answers', {})
        all_question_ids = request.data.get('question_ids', [])

        if not all_question_ids:
            raise ValidationError("A list of question IDs is required from the frontend.")

        questions = Question.objects.filter(id__in=all_question_ids)
        questions_map = {str(q.id): q for q in questions}
        
        user_answers_to_create = []
        correct_count = 0
        wrong_count = 0

        for q_id, selected_ans in answers_data.items():
            question = questions_map.get(str(q_id))
            if not question: continue

            is_correct = (selected_ans == question.correct_answer)
            if is_correct:
                correct_count += 1
            else:
                wrong_count += 1
            
            user_answers_to_create.append(
                UserAnswer(user=request.user, question=question, selected_option=selected_ans, is_correct=is_correct)
            )

        UserAnswer.objects.bulk_create(user_answers_to_create, ignore_conflicts=True)
        
        total_answered = len(answers_data)
        unanswered_count = len(all_question_ids) - total_answered
        final_score = (correct_count * 1) - (wrong_count * 0.33)

        # Award XP and update streak
        from questionbank.gamification import award_xp, update_streak
        xp_earned = (correct_count * 10) + (wrong_count * 2) + 50
        _, level_up, new_level = award_xp(request.user, xp_earned)
        current_streak, longest_streak, freeze_used, streak_promo_awarded = update_streak(request.user)

        response_data = {
            'results': {
                'score': round(final_score, 2),
                'total': len(all_question_ids),
                'correct': correct_count,
                'wrong': wrong_count,
                'unanswered': unanswered_count,
            },
            'questions': QuestionSerializer(questions, many=True).data,
            'gamification': {
                'xp_earned': xp_earned,
                'level_up': level_up,
                'new_level': new_level,
                'current_streak': current_streak,
                'longest_streak': longest_streak,
                'freeze_used': freeze_used,
                'streak_promo_awarded': streak_promo_awarded
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)
  # In questionbank/views.py

from rest_framework import views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Case, When, FloatField, F
from django.db.models.functions import Cast
from .models import UserAnswer, Topic, Question, Exam
from .serializers import DetailedUserAnswerSerializer

class MyProgressDashboardView(views.APIView):
    """
    Calculates and returns personalized, detailed progress stats. If no data exists for the
    user's focus exam, it automatically falls back to showing the overall report.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = user.userprofile
        
        mode = request.query_params.get('mode', 'focus')

        # Start with all of the user's answers, pre-fetching related data for efficiency
        all_answers = UserAnswer.objects.filter(user=user).select_related('question__topic')

        # This will be our final queryset for calculations
        answers_to_process = all_answers
        report_title = "Overall Report"

        if mode == 'focus':
            focus_exams = profile.preferred_exams.all()
            if not focus_exams.exists():
                return Response({
                    'report_title': report_title,
                    'overall_stats': {'total_answered': 0, 'correct': 0, 'wrong': 0, 'accuracy': 0, 'net_marks': 0},
                    'topic_performance': [],
                    'exam_performance': [],
                    'strongest_topics': [],
                    'weakest_topics': [],
                    'answer_history': [],
                    'heatmap_data': [],
                    'badges': [],
                    'no_data': True,
                    'message': "Please set one or more focus exams in your profile to see a personalized report."
                })
            
            report_title = f"Focus Report: {', '.join([exam.name for exam in focus_exams])}"
            # Filter answers to only include questions from the user's focus exams
            answers_to_process = all_answers.filter(question__exams__in=focus_exams).distinct()
        
        # --- Common badges helper ---
        import datetime
        from django.utils import timezone
        
        total_answered = answers_to_process.count()
        correct_count = answers_to_process.filter(is_correct=True).count()
        wrong_count = total_answered - correct_count
        net_marks = (correct_count * 1) - (wrong_count * 0.33)
        accuracy = (correct_count * 100.0 / total_answered) if total_answered > 0 else 0
        
        # Generate badges
        badges = [
            {
                'id': 'streak_3',
                'name': '3-Day Starter',
                'description': 'Maintained a 3-day study streak',
                'category': 'streak',
                'earned': profile.longest_streak >= 3,
                'icon': '🔥'
            },
            {
                'id': 'streak_7',
                'name': '7-Day Consistent',
                'description': 'Maintained a 7-day study streak',
                'category': 'streak',
                'earned': profile.longest_streak >= 7,
                'icon': '⚡'
            },
            {
                'id': 'streak_14',
                'name': '14-Day Habit',
                'description': 'Maintained a 14-day study streak',
                'category': 'streak',
                'earned': profile.longest_streak >= 14,
                'icon': '👑'
            },
            {
                'id': 'streak_30',
                'name': '30-Day Champion',
                'description': 'Maintained a 30-day study streak',
                'category': 'streak',
                'earned': profile.longest_streak >= 30,
                'icon': '🏆'
            },
            {
                'id': 'accuracy_perfect',
                'name': 'First Perfect Quiz',
                'description': 'Answered all questions correctly in a session',
                'category': 'accuracy',
                'earned': accuracy >= 100.0 and total_answered >= 5,
                'icon': '🎯'
            },
            {
                'id': 'volume_100',
                'name': '100 Questions',
                'description': 'Answered 100 questions in total',
                'category': 'volume',
                'earned': total_answered >= 100,
                'icon': '📚'
            },
            {
                'id': 'volume_500',
                'name': '500 Questions',
                'description': 'Answered 500 questions in total',
                'category': 'volume',
                'earned': total_answered >= 500,
                'icon': '💎'
            },
            {
                'id': 'volume_1000',
                'name': '1,000 Questions',
                'description': 'Answered 1,000 questions in total',
                'category': 'volume',
                'earned': total_answered >= 1000,
                'icon': '🌟'
            }
        ]

        if not answers_to_process.exists():
            return Response({
                'report_title': report_title,
                'overall_stats': {
                    'total_answered': 0,
                    'correct': 0,
                    'wrong': 0,
                    'accuracy': 0,
                    'net_marks': 0
                },
                'topic_performance': [],
                'exam_performance': [],
                'strongest_topics': [],
                'weakest_topics': [],
                'answer_history': [],
                'heatmap_data': [],
                'badges': badges,
                'no_data': True,
                'message': f"No progress data available yet for '{report_title}'. Start taking quizzes!"
            })
            
        # --- 1. Calculate Performance by Topic ---
        topic_performance = answers_to_process.values(
            'question__topic__name', 
            'question__topic__id'
        ).annotate(
            total=Count('id'),
            correct=Count(Case(When(is_correct=True, then=1)))
        ).annotate(
            wrong=F('total') - F('correct'),
            accuracy=Cast('correct', FloatField()) * 100.0 / F('total'),
            marks_lost=(F('wrong') * 1.33)
        )

        # --- 2. Calculate Performance by Exam ---
        exam_performance = answers_to_process.values(
            'question__exams__name' # Query through the M2M relationship
        ).annotate(
            total=Count('id'),
            correct=Count(Case(When(is_correct=True, then=1)))
        ).annotate(
            accuracy=Cast('correct', FloatField()) * 100.0 / F('total')
        )
        
        # --- 4. Get Recent Answer History ---
        recent_answers = answers_to_process.order_by('-answered_at')[:50]

        # --- 5. Generate Heatmap data for last 30 days ---
        today = timezone.localdate()
        thirty_days_ago = today - datetime.timedelta(days=30)
        daily_activity_qs = UserAnswer.objects.filter(
            user=user, 
            answered_at__date__gte=thirty_days_ago
        ).values('answered_at__date').annotate(count=Count('id')).order_by('answered_at__date')
        
        heatmap_dict = { (thirty_days_ago + datetime.timedelta(days=i)): 0 for i in range(31) }
        for entry in daily_activity_qs:
            heatmap_dict[entry['answered_at__date']] = entry['count']
            
        heatmap_data = [
            {'date': dt.strftime('%Y-%m-%d'), 'count': count}
            for dt, count in sorted(heatmap_dict.items())
        ]

        # --- 6. Assemble the final data object for the API response ---
        data = {
            'report_title': report_title,
            'overall_stats': {
                'total_answered': total_answered,
                'correct': correct_count,
                'wrong': wrong_count,
                'accuracy': round(accuracy, 2),
                'net_marks': round(net_marks, 2)
            },
            'topic_performance': list(topic_performance.order_by('-accuracy')),
            'exam_performance': list(exam_performance.order_by('-accuracy')),
            'strongest_topics': list(topic_performance.order_by('-accuracy')[:3]),
            'weakest_topics': list(topic_performance.filter(wrong__gt=0).order_by('-marks_lost')[:3]),
            'answer_history': DetailedUserAnswerSerializer(recent_answers, many=True).data,
            'heatmap_data': heatmap_data,
            'badges': badges
        }
        return Response(data)
# ===================================================================
# --- OTHER PROTECTED USER ACTION VIEWS ---
# ===================================================================

class BookmarkListCreateView(generics.ListCreateAPIView):
    serializer_class = BookmarkSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user).order_by('-created_at')
    def perform_create(self, serializer):
        question = serializer.validated_data.get('question')
        if not Bookmark.objects.filter(user=self.request.user, question=question).exists():
            serializer.save(user=self.request.user)

class ReportListCreateView(generics.ListCreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Report.objects.filter(user=self.request.user).order_by('-created_at')
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CreateJoinRequestView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = JoinRequestSerializer
    def perform_create(self, serializer):
        student_profile = self.request.user.userprofile
        institute_id = self.request.data.get('institute')
        if student_profile.institute:
            raise ValidationError("You already belong to an institute.")
        if InstituteJoinRequest.objects.filter(student_profile=student_profile, institute_id=institute_id, status='pending').exists():
            raise ValidationError("You already have a pending request to join this institute.")
        serializer.save(student_profile=student_profile, institute_id=institute_id)


# ===================================================================
# --- STUDENT MESSAGING VIEWS ---
# ===================================================================

class MyMessagesListView(generics.ListAPIView):
    serializer_class = ReceivedMessageSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return self.request.user.received_messages.all().order_by('-sent_at')

class MarkMessageAsReadView(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        message = get_object_or_404(Message, pk=pk)
        if request.user not in message.recipients.all():
            raise PermissionDenied("You are not a recipient of this message.")
        message.read_by.add(request.user)
        return Response(status=status.HTTP_200_OK)



# views.py
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.http import JsonResponse
from .models import DailyExam, Question
from .serializers import DailyExamSerializer
import json
import csv
from io import StringIO
from datetime import datetime


# This is the public API endpoint for your mobile app
class DailyExamListView(generics.ListAPIView):
    """
    Returns a list of the last 20 daily exam sets for the mobile app.
    """
    serializer_class = DailyExamSerializer
    permission_classes = [AllowAny]
    queryset = DailyExam.objects.all().order_by('-date')[:20]

from .models import Topic

class BulkUploadView:
    def process_questions_text(self, text_data):
        created_questions = []
        errors = []
        lines = text_data.strip().split('\n')
        default_topic = Topic.objects.get_or_create(name="General", defaults={'slug': 'general'})[0]

        for line in lines:
            try:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) < 6:
                    errors.append(f"Incomplete line: {line}")
                    continue

                q = Question.objects.create(
                    text=parts[0],
                    options={
                        'A': parts[1],
                        'B': parts[2],
                        'C': parts[3],
                        'D': parts[4],
                    },
                    correct_answer=parts[5].upper(),
                    explanation=parts[6] if len(parts) > 6 else '',
                    topic=default_topic,
                    difficulty='medium'
                )
                created_questions.append(q)

            except Exception as e:
                errors.append(f"{line} — {str(e)}")

        return {'created_questions': created_questions, 'errors': errors}



# In questionbank/views.py
from .models import DailyExamAttempt
from .serializers import SubmitDailyExamSerializer, DailyExamAttemptSerializer
# In questionbank/views.py
from .models import DailyExamAttempt

class SubmitDailyExamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        daily_exam = get_object_or_404(DailyExam, pk=pk)
        
        if DailyExamAttempt.objects.filter(user=request.user, daily_exam=daily_exam).exists():
            return Response({'detail': 'You have already attempted this daily exam.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SubmitDailyExamSerializer(data=request.data)
        if serializer.is_valid():
            answers = serializer.validated_data['answers']
            time_taken = serializer.validated_data['time_taken']
            
            correct_count = 0
            questions = daily_exam.questions.all()
            for q in questions:
                if str(q.id) in answers and answers[str(q.id)] == q.correct_answer:
                    correct_count += 1
            
            score = (correct_count / questions.count()) * 100 if questions.count() > 0 else 0

            DailyExamAttempt.objects.create(
                user=request.user, daily_exam=daily_exam, score=score, time_taken=time_taken
            )

            # Award XP and update streak
            from questionbank.gamification import award_xp, update_streak
            xp_earned = (correct_count * 10) + 50
            _, level_up, new_level = award_xp(request.user, xp_earned)
            current_streak, longest_streak, freeze_used, streak_promo_awarded = update_streak(request.user)

            return Response({
                'score': score, 
                'correct_count': correct_count, 
                'total_questions': questions.count(),
                'gamification': {
                    'xp_earned': xp_earned,
                    'level_up': level_up,
                    'new_level': new_level,
                    'current_streak': current_streak,
                    'longest_streak': longest_streak,
                    'freeze_used': freeze_used,
                    'streak_promo_awarded': streak_promo_awarded
                }
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DailyExamLeaderboardView(generics.ListAPIView):
    serializer_class = DailyExamAttemptSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        daily_exam_id = self.kwargs['pk']
        return DailyExamAttempt.objects.filter(daily_exam_id=daily_exam_id).order_by('-score', 'time_taken')[:50]



# In questionbank/views.py

# ===============================================================
# --- NEW: Model Exam Views (Simplified) ---
# ===============================================================

from .models import ModelExam, ModelExamAttempt
from .serializers import ModelExamSerializer, ModelExamDetailSerializer, SubmitDailyExamSerializer


class ModelExamListView(generics.ListAPIView):
    """Returns all model exams for a specific main exam."""
    serializer_class = ModelExamSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        exam_id = self.kwargs['exam_id']
        exam = get_object_or_404(Exam, pk=exam_id)
        words = [w for w in exam.name.replace('(', '').replace(')', '').replace('/', ' ').split() if len(w) > 2]
        similar_exams = Exam.objects.filter(id=exam.id)
        if words:
            q_obj = Q()
            for word in words:
                q_obj |= Q(name__icontains=word)
            similar_exams = Exam.objects.filter(q_obj)
        return ModelExam.objects.filter(exam__in=similar_exams)

class ModelExamDetailView(generics.RetrieveAPIView):
    """Returns the details and all questions for a single model exam."""
    queryset = ModelExam.objects.all()
    serializer_class = ModelExamDetailSerializer
    permission_classes = [IsAuthenticated]

# In questionbank/views.py

class SubmitModelExamView(APIView):
    """
    Handles submission of a model exam attempt and saves it for progress tracking.
    This version correctly allows users to retake exams.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        model_exam = get_object_or_404(ModelExam, pk=pk)
        
        # We can reuse the SubmitDailyExamSerializer
        serializer = SubmitDailyExamSerializer(data=request.data)
        if serializer.is_valid():
            answers = serializer.validated_data['answers']
            time_taken = serializer.validated_data.get('time_taken', 0)
            
            correct_count = 0
            questions = model_exam.questions.all()
            total_questions = questions.count()

            # --- This loop correctly calculates the score ---
            for question in questions:
                question_id_str = str(question.id)
                if question_id_str in answers and answers[question_id_str] == question.correct_answer:
                    correct_count += 1
            
            score = (correct_count / total_questions) * 100 if total_questions > 0 else 0

            # --- CORRECTED: Always create a new attempt for each submission ---
            ModelExamAttempt.objects.create(
                user=request.user, 
                model_exam=model_exam, 
                score=score, 
                time_taken=time_taken
            )

            # Award XP and update streak
            from questionbank.gamification import award_xp, update_streak
            xp_earned = (correct_count * 10) + 50
            _, level_up, new_level = award_xp(request.user, xp_earned)
            current_streak, longest_streak, freeze_used, streak_promo_awarded = update_streak(request.user)
            
            return Response({
                'score': score, 
                'correct_count': correct_count, 
                'total_questions': total_questions,
                'gamification': {
                    'xp_earned': xp_earned,
                    'level_up': level_up,
                    'new_level': new_level,
                    'current_streak': current_streak,
                    'longest_streak': longest_streak,
                    'freeze_used': freeze_used,
                    'streak_promo_awarded': streak_promo_awarded
                }
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# In questionbank/views.py
from .models import PreviousYearPaper
from .serializers import PreviousYearPaperSerializer

class PYQListView(generics.ListAPIView):
    serializer_class = PreviousYearPaperSerializer
    permission_classes = [IsAuthenticated] # Or AllowAny if you want guests to see the list

    def get_queryset(self):
        # Returns all PYQ papers for a specific main exam
        exam_id = self.kwargs['exam_id']
        exam = get_object_or_404(Exam, pk=exam_id)
        words = [w for w in exam.name.replace('(', '').replace(')', '').replace('/', ' ').split() if len(w) > 2]
        similar_exams = Exam.objects.filter(id=exam.id)
        if words:
            q_obj = Q()
            for word in words:
                q_obj |= Q(name__icontains=word)
            similar_exams = Exam.objects.filter(q_obj)
        return PreviousYearPaper.objects.filter(exam__in=similar_exams)



# In questionbank/views.py
from .models import Syllabus, ExamAnnouncement
from .serializers import SyllabusSerializer, ExamAnnouncementSerializer
from django.utils import timezone   

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

class ExamSyllabusListView(generics.ListAPIView):
    serializer_class = SyllabusSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Syllabus.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = list(serializer.data)
        
        # Auto-generate Syllabus text if no direct Syllabus object exists
        from .models import Exam, ExamSyllabus
        from django.db.models import Q, Count
        
        exams_with_syllabus = set(Syllabus.objects.values_list('exam_id', flat=True))
        exams = Exam.objects.all()
        
        for exam in exams:
            # If a direct Syllabus object exists, it is already serialized in `data`
            if exam.id in exams_with_syllabus:
                continue
                
            # Check for similar exams to inherit syllabus details if they exist
            words = [w for w in exam.name.replace('(', '').replace(')', '').replace('/', ' ').split() if len(w) > 2]
            similar_syllabus = None
            if words:
                q_obj = Q()
                for word in words:
                    q_obj |= Q(name__icontains=word)
                similar_exams = Exam.objects.filter(q_obj)
                similar_syllabus = Syllabus.objects.filter(exam__in=similar_exams).first()
                
            # If we found a similar syllabus, inherit it
            if similar_syllabus:
                pdf_url = None
                if similar_syllabus.pdf_file and hasattr(similar_syllabus.pdf_file, 'url'):
                    pdf_url = request.build_absolute_uri(similar_syllabus.pdf_file.url)
                    
                # Calculate weights for this specific exam if it has syllabus parts
                parts = exam.syllabus_parts.all()
                total_qs = sum(p.num_questions for p in parts)
                weights = []
                if total_qs > 0:
                    consolidated = {}
                    for p in parts:
                        subject = get_consolidated_subject(p.topic.name)
                        consolidated[subject] = consolidated.get(subject, 0) + p.num_questions
                    weights = [
                        {"subject": sub, "weight": round((count / total_qs) * 100, 1)}
                        for sub, count in consolidated.items()
                    ]
                    
                data.append({
                    'id': -exam.id,
                    'exam': exam.id,
                    'exam_name': exam.name,
                    'details': similar_syllabus.details,
                    'pdf_file_url': pdf_url,
                    'subject_weights': weights
                })
                exams_with_syllabus.add(exam.id)
                continue
                
            # Try Option 2: Auto-generate from ExamSyllabus parts of this or similar exams
            similar_exams_ids = [exam.id]
            if words:
                q_obj = Q()
                for word in words:
                    q_obj |= Q(name__icontains=word)
                similar_exams_ids = list(Exam.objects.filter(q_obj).values_list('id', flat=True))
                
            parts = ExamSyllabus.objects.filter(exam_id__in=similar_exams_ids)
            if parts.exists():
                topics_desc = []
                total_qs = 0
                for part in parts:
                    topics_desc.append(f"- {part.topic.name} ({part.num_questions} questions)")
                    total_qs += part.num_questions
                    
                # Specific details based on exam type
                details = ""
                name_lower = exam.name.lower()
                if 'ldc' in name_lower or 'clerk' in name_lower:
                    details = (
                        "### Part I: General Knowledge (50 Marks)\n"
                        "History (5 Marks), Geography (5 Marks), Economics (5 Marks), Constitution (5 Marks), "
                        "Kerala Governance (5 Marks), Life Science & Health (6 Marks), Physical Science (3 Marks), "
                        "Chemistry (3 Marks), Arts/Sports/Literature/Culture (5 Marks), Computer Basics (3 Marks), "
                        "Important Laws (RTI, Consumer, POCSO, Domestic Violence - 5 Marks).\n\n"
                        "### Part II: Current Affairs (20 Marks)\n"
                        "Recent national and international events in science, technology, arts, culture, politics, economy, literature, and sports.\n\n"
                        "### Part III: Simple Arithmetic, Mental Ability & Observation Skills (10 Marks)\n"
                        "Simple Arithmetic (5 Marks), Mental Ability and Observation Skills (5 Marks).\n\n"
                        "### Part IV: General English (10 Marks)\n"
                        "Grammar (5 Marks) and Vocabulary (5 Marks).\n\n"
                        "### Part V: Regional Language – Malayalam/Kannada/Tamil (10 Marks)\n"
                        "Regional language spelling, grammar, proverbs, and translations."
                    )
                elif 'lgs' in name_lower or 'servant' in name_lower:
                    details = (
                        "### Part I: General Knowledge (50 Marks)\n"
                        "History, Geography, Economics, Civics, Kerala Renaissance, and General GK.\n\n"
                        "### Part II: General Science (20 Marks)\n"
                        "Natural Science (Life Science) (10 Marks) and Physical Science (Physics & Chemistry) (10 Marks).\n\n"
                        "### Part III: Simple Arithmetic & Mental Ability (20 Marks)\n"
                        "Simple Arithmetic (10 Marks) and Mental Ability (10 Marks).\n\n"
                        "### Part IV: Current Affairs (10 Marks)\n"
                        "Latest national and international events."
                    )
                else:
                    details = f"Official Mock Exam Syllabus for {exam.name}.\n\n"
                    details += f"Total Questions: {total_qs}\n"
                    details += f"Duration: {exam.duration_minutes} minutes\n\n"
                    details += "Subject Weightages & Topics:\n"
                    details += "\n".join(sorted(list(set(topics_desc))))
                
                # Specific weights for this exam
                exam_parts = exam.syllabus_parts.all()
                exam_total_qs = sum(p.num_questions for p in exam_parts)
                weights = []
                if exam_total_qs > 0:
                    consolidated = {}
                    for p in exam_parts:
                        subject = get_consolidated_subject(p.topic.name)
                        consolidated[subject] = consolidated.get(subject, 0) + p.num_questions
                    weights = [
                        {"subject": sub, "weight": round((count / exam_total_qs) * 100, 1)}
                        for sub, count in consolidated.items()
                    ]
                else:
                    consolidated = {}
                    for part in parts:
                        subject = get_consolidated_subject(part.topic.name)
                        consolidated[subject] = consolidated.get(subject, 0) + part.num_questions
                    weights = [
                        {"subject": sub, "weight": round((count / total_qs) * 100, 1)}
                        for sub, count in consolidated.items()
                    ]
                    
                exams_with_syllabus.add(exam.id)
                data.append({
                    'id': -exam.id,
                    'exam': exam.id,
                    'exam_name': exam.name,
                    'details': details,
                    'pdf_file_url': None,
                    'subject_weights': weights
                })
                continue

            # Try Option 3: Auto-generate from the actual questions associated with this/similar exams
            similar_exams_qs = Exam.objects.filter(id__in=similar_exams_ids)
            exam_questions = Question.objects.filter(exams__in=similar_exams_qs)
            if exam_questions.exists():
                topic_counts = exam_questions.values('topic__name').annotate(count=Count('id')).order_by('-count')
                total_qs = exam_questions.count()
                
                consolidated = {}
                for entry in topic_counts:
                    topic_name = entry['topic__name'] or "General Topics"
                    count = entry['count']
                    subject = get_consolidated_subject(topic_name)
                    consolidated[subject] = consolidated.get(subject, 0) + count
                    
                weights = [
                    {"subject": sub, "weight": round((count / total_qs) * 100, 1)}
                    for sub, count in consolidated.items()
                ]
                
                details = ""
                name_lower = exam.name.lower()
                if 'ldc' in name_lower or 'clerk' in name_lower:
                    details = (
                        "### Part I: General Knowledge (50 Marks)\n"
                        "History (5 Marks), Geography (5 Marks), Economics (5 Marks), Constitution (5 Marks), "
                        "Kerala Governance (5 Marks), Life Science & Health (6 Marks), Physical Science (3 Marks), "
                        "Chemistry (3 Marks), Arts/Sports/Literature/Culture (5 Marks), Computer Basics (3 Marks), "
                        "Important Laws (RTI, Consumer, POCSO, Domestic Violence - 5 Marks).\n\n"
                        "### Part II: Current Affairs (20 Marks)\n"
                        "Recent national and international events in science, technology, arts, culture, politics, economy, literature, and sports.\n\n"
                        "### Part III: Simple Arithmetic, Mental Ability & Observation Skills (10 Marks)\n"
                        "Simple Arithmetic (5 Marks), Mental Ability and Observation Skills (5 Marks).\n\n"
                        "### Part IV: General English (10 Marks)\n"
                        "Grammar (5 Marks) and Vocabulary (5 Marks).\n\n"
                        "### Part V: Regional Language – Malayalam/Kannada/Tamil (10 Marks)\n"
                        "Regional language spelling, grammar, proverbs, and translations."
                    )
                elif 'lgs' in name_lower or 'servant' in name_lower:
                    details = (
                        "### Part I: General Knowledge (50 Marks)\n"
                        "History, Geography, Economics, Civics, Kerala Renaissance, and General GK.\n\n"
                        "### Part II: General Science (20 Marks)\n"
                        "Natural Science (Life Science) (10 Marks) and Physical Science (Physics & Chemistry) (10 Marks).\n\n"
                        "### Part III: Simple Arithmetic & Mental Ability (20 Marks)\n"
                        "Simple Arithmetic (10 Marks) and Mental Ability (10 Marks).\n\n"
                        "### Part IV: Current Affairs (10 Marks)\n"
                        "Latest national and international events."
                    )
                else:
                    details = f"Curated Mock Exam Syllabus for {exam.name} (based on question distribution).\n\n"
                    details += f"Total Questions: 100\n"
                    details += f"Duration: {exam.duration_minutes} minutes\n\n"
                
                data.append({
                    'id': -exam.id,
                    'exam': exam.id,
                    'exam_name': exam.name,
                    'details': details,
                    'pdf_file_url': None,
                    'subject_weights': weights
                })
                exams_with_syllabus.add(exam.id)
                continue

            # Option 4: Generic default syllabus fallback based on name matching
            default_weights = []
            details = ""
            name_lower = exam.name.lower()
            if 'ldc' in name_lower or 'clerk' in name_lower:
                details = (
                    "### Part I: General Knowledge (50 Marks)\n"
                    "History (5 Marks), Geography (5 Marks), Economics (5 Marks), Constitution (5 Marks), "
                    "Kerala Governance (5 Marks), Life Science & Health (6 Marks), Physical Science (3 Marks), "
                    "Chemistry (3 Marks), Arts/Sports/Literature/Culture (5 Marks), Computer Basics (3 Marks), "
                    "Important Laws (RTI, Consumer, POCSO, Domestic Violence - 5 Marks).\n\n"
                    "### Part II: Current Affairs (20 Marks)\n"
                    "Recent national and international events in science, technology, arts, culture, politics, economy, literature, and sports.\n\n"
                    "### Part III: Simple Arithmetic, Mental Ability & Observation Skills (10 Marks)\n"
                    "Simple Arithmetic (5 Marks), Mental Ability and Observation Skills (5 Marks).\n\n"
                    "### Part IV: General English (10 Marks)\n"
                    "Grammar (5 Marks) and Vocabulary (5 Marks).\n\n"
                    "### Part V: Regional Language – Malayalam/Kannada/Tamil (10 Marks)\n"
                    "Regional language spelling, grammar, proverbs, and translations."
                )
                default_weights = [
                    {"subject": "General Knowledge & Renaissance", "weight": 50.0},
                    {"subject": "Current Affairs", "weight": 20.0},
                    {"subject": "Simple Arithmetic & Mental Ability", "weight": 10.0},
                    {"subject": "General English", "weight": 10.0},
                    {"subject": "Regional Language (Malayalam/Kannada/Tamil)", "weight": 10.0}
                ]
            elif 'lgs' in name_lower or 'servant' in name_lower:
                details = (
                    "### Part I: General Knowledge (40 Marks)\n"
                    "Indian Freedom Struggle, Post-Independence India, Fundamental Rights & Duties, "
                    "Geographical features of India, Kerala Geography & Renaissance, Arts/Sports/Culture.\n\n"
                    "### Part II: Current Affairs (20 Marks)\n"
                    "Recent national and international events in science, technology, arts, culture, "
                    "politics, economy, literature, and sports.\n\n"
                    "### Part III: Science (10 Marks)\n"
                    "Life Science/Biology (5 Marks): Human body, vitamins, crops, forestry, environment.\n"
                    "Physical Science/Chemistry (5 Marks): Atoms, minerals, elements, matter, energy, solar system.\n\n"
                    "### Part IV: Public Health (10 Marks)\n"
                    "Communicable diseases, basic health knowledge, lifestyle diseases, health welfare in Kerala.\n\n"
                    "### Part V: Simple Arithmetic, Mental Ability & Observation Skills (20 Marks)\n"
                    "Simple Arithmetic (10 Marks): Numbers, LCM/HCF, fractions, averages, profit/loss, time/distance.\n"
                    "Mental Ability (10 Marks): Series, analogies, classification, odd one out, age problems."
                )
                default_weights = [
                    {"subject": "Part I: General Knowledge", "weight": 40.0},
                    {"subject": "Part II: Current Affairs", "weight": 20.0},
                    {"subject": "Part III: Science", "weight": 10.0},
                    {"subject": "Part IV: Public Health", "weight": 10.0},
                    {"subject": "Part V: Simple Arithmetic & Mental Ability", "weight": 20.0}
                ]
            elif 'constable' in name_lower or 'cpo' in name_lower or 'police' in name_lower:
                details = (
                    "### Part I: General Knowledge (40 Marks)\n"
                    "History (5), Geography (5), Economics (5), Indian Constitution (8), Kerala Governance (3), "
                    "Life Science & Public Health (4), Physical Science (3), Chemistry (3), Arts/Sports/Literature/Culture (4).\n\n"
                    "### Part II: Current Affairs (10 Marks)\n"
                    "Recent national and international events.\n\n"
                    "### Part III: Simple Arithmetic, Mental Ability & Observation Skills (10 Marks)\n"
                    "Simple Arithmetic (5 Marks) and Mental Ability/Observation Skills (5 Marks).\n\n"
                    "### Part IV: General English (10 Marks)\n"
                    "Grammar (5 Marks) and Vocabulary (5 Marks).\n\n"
                    "### Part V: Regional Language – Malayalam/Kannada/Tamil (10 Marks)\n"
                    "Word purity, sentence correction, translation, synonyms, antonyms, idioms.\n\n"
                    "### Part VI: Special Topics – Job-Related Subjects (20 Marks)\n"
                    "IPC/BNS Offences, CrPC/BNSS, Evidence Act, Kerala Police Act, NDPS, POCSO, IT Act, RTI."
                )
                default_weights = [
                    {"subject": "Part I: General Knowledge", "weight": 40.0},
                    {"subject": "Part II: Current Affairs", "weight": 10.0},
                    {"subject": "Part III: Simple Arithmetic & Mental Ability", "weight": 10.0},
                    {"subject": "Part IV: General English", "weight": 10.0},
                    {"subject": "Part V: Regional Language", "weight": 10.0},
                    {"subject": "Part VI: Special Topics (Job-Related)", "weight": 20.0}
                ]
            elif 'degree' in name_lower or 'graduate' in name_lower:
                details = (
                    "### Part I: General Knowledge (65 Marks)\n"
                    "History (10), Geography (5), Economics (5), Civics (5), Indian Constitution (5), "
                    "Arts/Sports/Literature/Culture (10), Computer Science (5), Science & Technology (5), Current Affairs.\n\n"
                    "### Part II: Simple Arithmetic, Mental Ability and Reasoning (20 Marks)\n"
                    "Simple Arithmetic (10 Marks) and Mental Ability (10 Marks).\n\n"
                    "### Part III: General English (20 Marks)\n"
                    "Grammar (10 Marks) and Vocabulary (10 Marks).\n\n"
                    "### Part IV: Regional Language – Malayalam/Kannada/Tamil (10 Marks)\n"
                    "Regional language proficiency."
                )
                default_weights = [
                    {"subject": "Part I: General Knowledge", "weight": 50.0},
                    {"subject": "Part II: Simple Arithmetic & Mental Ability", "weight": 20.0},
                    {"subject": "Part III: General English", "weight": 20.0},
                    {"subject": "Part IV: Regional Language", "weight": 10.0}
                ]
            else:
                details = (
                    "### Part I: General Studies & Current Affairs (40 Marks)\n"
                    "History, Geography, Constitution, General Science, and Current Affairs.\n\n"
                    "### Part II: Simple Arithmetic & Mental Ability (20 Marks)\n"
                    "Numerical ability, logical reasoning, and calculations.\n\n"
                    "### Part III: General English (20 Marks)\n"
                    "English grammar, sentence structures, and vocabulary.\n\n"
                    "### Part IV: Regional Language (20 Marks)\n"
                    "Regional language grammar, comprehension, and translations."
                )
                default_weights = [
                    {"subject": "General Studies & Current Affairs", "weight": 40.0},
                    {"subject": "Simple Arithmetic & Mental Ability", "weight": 20.0},
                    {"subject": "General English", "weight": 20.0},
                    {"subject": "Regional Language", "weight": 20.0}
                ]
            
            data.append({
                'id': -exam.id,
                'exam': exam.id,
                'exam_name': exam.name,
                'details': details,
                'pdf_file_url': None,
                'subject_weights': default_weights
            })
            exams_with_syllabus.add(exam.id)
            
        return Response(data)


class ExamCalendarView(generics.ListAPIView):
    """
    Returns a list of all exam announcements (PDFs), ordered by date.
    """
    queryset = ExamAnnouncement.objects.all().order_by('-publication_date')
    serializer_class = ExamAnnouncementSerializer
    permission_classes = [AllowAny]



class PublicUserProfileView(generics.RetrieveAPIView):
    """
    Provides a public view of a user's profile, looked up by username.
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [AllowAny]
    lookup_field = 'user__username'
    lookup_url_kwarg = 'username'


from .models import CurrentAffairs
from .serializers import CurrentAffairsSerializer

class PublicQuestionDetailView(generics.RetrieveAPIView):
    """
    Public SEO endpoint to fetch a single question by its unique slug.
    """
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

class PublicTopicDetailView(generics.RetrieveAPIView):
    """
    Public SEO endpoint to fetch a single topic by its slug.
    """
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

class PublicExamDetailView(generics.RetrieveAPIView):
    """
    Public SEO endpoint to fetch a single exam by its slug.
    """
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

class PublicCurrentAffairsListView(generics.ListAPIView):
    """
    Public SEO endpoint to list recent current affairs.
    """
    queryset = CurrentAffairs.objects.all()
    serializer_class = CurrentAffairsSerializer
    permission_classes = [AllowAny]

class PublicCurrentAffairsDetailView(generics.RetrieveAPIView):
    """
    Public SEO endpoint to fetch a single current affair entry by slug.
    """
    queryset = CurrentAffairs.objects.all()
    serializer_class = CurrentAffairsSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


def seed_feed_cards():
    # Seed new cards using questions and current affairs not already in StudyFeedCard
    from questionbank.models import Question, CurrentAffairs, StudyFeedCard
    
    # 1. Convert new Questions into cards
    existing_q_ids = []
    for card in StudyFeedCard.objects.filter(card_type='question'):
        if isinstance(card.content_data, dict):
            q_id = card.content_data.get('question_id')
            if q_id:
                existing_q_ids.append(q_id)
                
    questions = Question.objects.exclude(id__in=existing_q_ids).order_by('?')[:15]
    for q in questions:
        content = {
            'question_id': q.id,
            'question_text': q.text,
            'options': q.options,
            'correct_answer': q.correct_answer,
            'explanation': q.explanation
        }
        StudyFeedCard.objects.create(
            card_type='question',
            title=f"Question on {q.topic.name if q.topic else 'General'}",
            content_data=content,
            psc_likelihood_tag='🔥'
        )
        
    # 2. Convert new Current Affairs into cards
    existing_ca_ids = []
    for card in StudyFeedCard.objects.filter(card_type='current_affairs'):
        if isinstance(card.content_data, dict):
            ca_id = card.content_data.get('ca_id')
            if ca_id:
                existing_ca_ids.append(ca_id)
                
    ca_items = CurrentAffairs.objects.exclude(id__in=existing_ca_ids).order_by('?')[:10]
    for ca in ca_items:
        content = {
            'ca_id': ca.id,
            'content': ca.content,
            'category': ca.category,
            'publication_date': ca.publication_date.isoformat() if ca.publication_date else None,
            'ai_summary': ca.ai_summary
        }
        StudyFeedCard.objects.create(
            card_type='current_affairs',
            title=ca.title,
            content_data=content,
            psc_likelihood_tag='💡'
        )

    # 3. Add some general fun facts for PSC (only if they don't exist)
    facts = [
        ("Largest District in Kerala", "Palakkad is the largest district in Kerala by area.", "💡"),
        ("Smallest District in Kerala", "Alappuzha is the smallest district in Kerala by area.", "💡"),
        ("Most Populous District in Kerala", "Malappuram is the most populous district in Kerala.", "🔥"),
        ("Least Populous District in Kerala", "Wayanad is the least populous district in Kerala.", "💡"),
        ("Longest River in Kerala", "Periyar is the longest river in Kerala with a length of 244 km.", "🔥"),
    ]
    for title, text, tag in facts:
        StudyFeedCard.objects.get_or_create(
            card_type='fact',
            title=title,
            content_data={'fact_text': text},
            psc_likelihood_tag=tag
        )


from subscriptions.utils import get_user_entitlement
from questionbank.models import StudyFeedCard, UserFeedView
from questionbank.serializers import StudyFeedCardSerializer

class StudyFeedView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Determine the user's daily feed limit
        limit = get_user_entitlement(request.user, 'feed_limit', 15)
        
        # 2. Count views today
        today = timezone.localdate()
        today_views = UserFeedView.objects.filter(user=request.user, viewed_date=today).count()
        
        if today_views >= limit:
            return Response({
                'limit_exceeded': True,
                'message': f"You have reached your daily feed limit of {limit} cards. Upgrade your plan to read unlimited cards!",
                'views_today': today_views,
                'limit': limit,
                'cards': []
            }, status=status.HTTP_200_OK)
            
        # 3. Auto-seed if unviewed cards for this user today are low
        viewed_ids = UserFeedView.objects.filter(user=request.user, viewed_date=today).values_list('card_id', flat=True)
        unviewed_count = StudyFeedCard.objects.exclude(id__in=viewed_ids).count()
        
        if unviewed_count < 10:
            try:
                seed_feed_cards()
            except Exception:
                pass
                
        # 4. Get available cards (exclude what they saw today)
        viewed_ids = UserFeedView.objects.filter(user=request.user, viewed_date=today).values_list('card_id', flat=True)
        available_cards = list(StudyFeedCard.objects.exclude(id__in=viewed_ids).order_by('?')[:10])
        
        # If no more cards in DB, we can re-use cards
        if not available_cards:
            available_cards = list(StudyFeedCard.objects.order_by('?')[:10])
            
        # 5. Inject Quiz Card every 5 cards
        final_cards = []
        for i, card in enumerate(available_cards):
            final_cards.append(StudyFeedCardSerializer(card).data)
            if (i + 1) % 5 == 0:
                random_q = Question.objects.all().order_by('?').first()
                if random_q:
                    final_cards.append({
                        'id': f"quiz-injected-{random_q.id}",
                        'card_type': 'question',
                        'title': "Quick Knowledge Check!",
                        'content_data': {
                            'question_id': random_q.id,
                            'question_text': random_q.text,
                            'options': random_q.options,
                            'correct_answer': random_q.correct_answer,
                            'explanation': random_q.explanation
                        },
                        'psc_likelihood_tag': '🔥'
                    })
                    
        return Response({
            'limit_exceeded': False,
            'views_today': today_views,
            'limit': limit,
            'cards': final_cards
        })

class RecordCardView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        card_id = request.data.get('card_id')
        if not card_id:
            return Response({'error': 'card_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        if isinstance(card_id, str) and card_id.startswith('quiz-injected-'):
            return Response({'success': True})
            
        try:
            card = StudyFeedCard.objects.get(pk=card_id)
        except StudyFeedCard.DoesNotExist:
            return Response({'error': 'Card does not exist'}, status=status.HTTP_404_NOT_FOUND)
            
        today = timezone.localdate()
        limit = get_user_entitlement(request.user, 'feed_limit', 15)
        today_views = UserFeedView.objects.filter(user=request.user, viewed_date=today).count()
        
        if today_views >= limit:
            return Response({
                'limit_exceeded': True,
                'message': "Daily feed limit reached."
            }, status=status.HTTP_403_FORBIDDEN)
            
        UserFeedView.objects.get_or_create(user=request.user, card=card, viewed_date=today)
        new_views_count = UserFeedView.objects.filter(user=request.user, viewed_date=today).count()
        
        return Response({
            'success': True,
            'views_today': new_views_count,
            'limit': limit
        })

class QuestionExplanationView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        lang = request.query_params.get('lang', 'en')
        if lang not in ('en', 'ml'):
            lang = 'en'
            
        from questionbank.ai_adapter import get_ai_explanation
        explanation = get_ai_explanation(question, lang)
        
        return Response({
            'question_id': question.id,
            'language': lang,
            'explanation': explanation
        })


class LeaderboardView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        
        # 1. All Kerala Leaderboard
        all_kerala_profiles = UserProfile.objects.select_related('user').order_by('-total_xp', 'id')
        all_kerala = []
        user_position_all = None
        for index, p in enumerate(all_kerala_profiles):
            data = {
                'rank': index + 1,
                'username': p.user.username,
                'avatar': p.profile_photo.url if p.profile_photo else None,
                'place': p.get_district_display() if p.district else (p.place or "Kerala"),
                'xp': p.total_xp,
                'streak': p.current_streak,
                'level': p.level
            }
            all_kerala.append(data)
            if p.user == user:
                user_position_all = data
                user_position_all['places_gained'] = "+3"

        # Limit to top 50, but user position needs to be calculated from full list
        all_kerala_limited = all_kerala[:50]

        # 2. District Leaderboard
        district = profile.district
        district_profiles = []
        user_position_district = None
        if district:
            dist_profiles = UserProfile.objects.filter(district=district).select_related('user').order_by('-total_xp', 'id')
            for index, p in enumerate(dist_profiles):
                data = {
                    'rank': index + 1,
                    'username': p.user.username,
                    'avatar': p.profile_photo.url if p.profile_photo else None,
                    'place': p.get_district_display() or "Kerala",
                    'xp': p.total_xp,
                    'streak': p.current_streak,
                    'level': p.level
                }
                district_profiles.append(data)
                if p.user == user:
                    user_position_district = data
                    user_position_district['places_gained'] = "+2"
        else:
            # Fallback if no district set
            district_profiles = all_kerala_limited
            user_position_district = user_position_all

        district_limited = district_profiles[:50]

        # 3. Batch/Institute Leaderboard
        batch_profiles = []
        user_position_batch = None
        if profile.institute:
            inst_profiles = UserProfile.objects.filter(institute=profile.institute).select_related('user').order_by('-total_xp', 'id')
            for index, p in enumerate(inst_profiles):
                data = {
                    'rank': index + 1,
                    'username': p.user.username,
                    'avatar': p.profile_photo.url if p.profile_photo else None,
                    'place': p.get_district_display() if p.district else (p.place or "Kerala"),
                    'xp': p.total_xp,
                    'streak': p.current_streak,
                    'level': p.level
                }
                batch_profiles.append(data)
                if p.user == user:
                    user_position_batch = data
                    user_position_batch['places_gained'] = "+1"
        else:
            # Fallback if no institute
            batch_profiles = all_kerala_limited
            user_position_batch = user_position_all

        batch_limited = batch_profiles[:50]

        # 4. Friends Leaderboard (Symmetrical friends ranking)
        friend_profiles = UserProfile.objects.filter(
            Q(id=profile.id) | Q(friends=profile)
        ).distinct().select_related('user').order_by('-total_xp', 'id')
        
        friends_list = []
        user_position_friends = None
        for index, p in enumerate(friend_profiles):
            data = {
                'rank': index + 1,
                'username': p.user.username,
                'avatar': p.profile_photo.url if p.profile_photo else None,
                'place': p.get_district_display() if p.district else (p.place or "Kerala"),
                'xp': p.total_xp,
                'streak': p.current_streak,
                'level': p.level
            }
            friends_list.append(data)
            if p.user == user:
                user_position_friends = data
                user_position_friends['places_gained'] = "+1"

        friends_limited = friends_list[:50]

        return Response({
            'all_kerala': all_kerala_limited,
            'district': district_limited,
            'batch': batch_limited,
            'friends': friends_limited,
            'user_position': user_position_all or {
                'rank': 0, 'username': user.username, 'avatar': None, 'place': '', 'xp': profile.total_xp, 'streak': profile.current_streak, 'level': profile.level, 'places_gained': "0"
            },
            'user_position_district': user_position_district,
            'user_position_batch': user_position_batch,
            'user_position_friends': user_position_friends,
        })


class WrongAnswersView(generics.ListAPIView):
    serializer_class = DetailedUserAnswerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserAnswer.objects.filter(user=self.request.user, is_correct=False).select_related('question__topic').order_by('-answered_at')


class WeeklyGoalsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        
        # Calculate weekly stats: Monday 00:00 to now
        import datetime
        from django.utils import timezone
        
        now = timezone.now()
        start_of_week = now - datetime.timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 1. Answer 50 questions
        questions_answered = UserAnswer.objects.filter(user=user, answered_at__gte=start_of_week).count()
        
        # 2. Complete 2 mock tests
        mock_tests_completed = ModelExamAttempt.objects.filter(user=user, submitted_at__gte=start_of_week).count()
        
        # 3. Read 10 current affairs
        ca_read = UserFeedView.objects.filter(user=user, card__card_type='current_affairs', viewed_date__gte=start_of_week.date()).count()
        
        # 4. Review wrong answers
        wrong_count = UserAnswer.objects.filter(user=user, is_correct=False).count()
        # count how many wrong answers corrected/answered correct this week
        wrong_reviewed = UserAnswer.objects.filter(user=user, answered_at__gte=start_of_week, is_correct=True, question__user_answers__user=user, question__user_answers__is_correct=False).distinct().count()
        
        # 5. Maintain streak
        streak = profile.current_streak
        
        missions = [
            {
                'id': 'questions_50',
                'text': 'Answer 50 questions',
                'progress': min(questions_answered, 50),
                'target': 50,
                'xp_reward': 100,
                'completed': questions_answered >= 50
            },
            {
                'id': 'mock_tests_2',
                'text': 'Complete 2 mock tests',
                'progress': min(mock_tests_completed, 2),
                'target': 2,
                'xp_reward': 150,
                'completed': mock_tests_completed >= 2
            },
            {
                'id': 'current_affairs_10',
                'text': 'Read 10 current affairs',
                'progress': min(ca_read, 10),
                'target': 10,
                'xp_reward': 75,
                'completed': ca_read >= 10
            },
            {
                'id': 'review_wrong',
                'text': 'Review wrong answers (Answer 5 previously wrong)',
                'progress': min(wrong_reviewed, 5) if wrong_count > 0 else 5,
                'target': 5,
                'xp_reward': 50,
                'completed': wrong_reviewed >= 5 if wrong_count > 0 else True
            },
            {
                'id': 'streak_7',
                'text': 'Maintain 7-day streak',
                'progress': min(streak, 7),
                'target': 7,
                'xp_reward': 200,
                'completed': streak >= 7
            }
        ]
        
        return Response({
            'missions': missions,
            'preferred_exams': [exam.name for exam in profile.preferred_exams.all()],
            'place': profile.place,
            'xp': profile.total_xp
        })


# ===================================================================
# --- STUDY FLOW & ANALYTICS VIEWS ---
# ===================================================================
from rest_framework import generics, views, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination

from .models import TopicProgress, PracticeSession, SessionAnswer, Topic, Question, UserAnswer
from .serializers import (
    TopicListSerializer, QuestionSerializer, QuestionResultSerializer,
    PracticeSessionSerializer, SessionAnswerSerializer
)

class TopicListView(generics.ListAPIView):
    serializer_class = TopicListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base_query = Q(institute__isnull=True)
        if hasattr(user, 'userprofile') and user.userprofile.institute:
            base_query |= Q(institute=user.userprofile.institute)
            
        preferred_exams = Exam.objects.none()
        if user and user.is_authenticated and hasattr(user, 'userprofile'):
            user_prefs = user.userprofile.preferred_exams.all()
            if user_prefs.exists():
                q_obj = Q()
                for exam in user_prefs:
                    q_obj |= Q(id=exam.id)
                    words = [w for w in exam.name.replace('(', '').replace(')', '').replace('/', ' ').split() if len(w) > 2]
                    if words:
                        sub_q = Q()
                        for word in words:
                            sub_q |= Q(name__icontains=word)
                        q_obj |= sub_q
                preferred_exams = Exam.objects.filter(q_obj).distinct()

        if preferred_exams.exists():
            syllabus_topics = Topic.objects.filter(examsyllabus__exam__in=preferred_exams).distinct()
            if syllabus_topics.exists():
                base_query &= Q(id__in=syllabus_topics)
                
        return Topic.objects.filter(base_query).distinct().order_by('name')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class TopicQuestionsPagination(PageNumberPagination):
    page_size = 20


class TopicQuestionsView(generics.ListAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TopicQuestionsPagination

    def get_queryset(self):
        slug = self.kwargs.get('slug')
        topic = get_object_or_404(Topic, slug=slug)
        user = self.request.user
        
        base_query = Q(topic=topic, institute__isnull=True)
        if hasattr(user, 'userprofile') and user.userprofile.institute:
            base_query |= Q(topic=topic, institute=user.userprofile.institute)
            
        qs = Question.objects.filter(base_query).distinct()
        
        preferred_exams = Exam.objects.none()
        if user and user.is_authenticated and hasattr(user, 'userprofile'):
            user_prefs = user.userprofile.preferred_exams.all()
            if user_prefs.exists():
                q_obj = Q()
                for exam in user_prefs:
                    q_obj |= Q(id=exam.id)
                    words = [w for w in exam.name.replace('(', '').replace(')', '').replace('/', ' ').split() if len(w) > 2]
                    if words:
                        sub_q = Q()
                        for word in words:
                            sub_q |= Q(name__icontains=word)
                        q_obj |= sub_q
                preferred_exams = Exam.objects.filter(q_obj).distinct()

        if preferred_exams.exists():
            syllabus_topics = Topic.objects.filter(examsyllabus__exam__in=preferred_exams).distinct()
            exam_filter = Q(exams__in=preferred_exams)
            if syllabus_topics.exists():
                exam_filter |= Q(topic__in=syllabus_topics)
            qs = qs.filter(exam_filter).distinct()
        
        difficulty = self.request.query_params.get('difficulty')
        if difficulty in ('easy', 'medium', 'hard'):
            qs = qs.filter(difficulty=difficulty)
            
        exclude_answered = self.request.query_params.get('exclude_answered', 'false')
        if exclude_answered.lower() == 'true':
            answered_correct_ids = UserAnswer.objects.filter(
                user=user, is_correct=True
            ).values_list('question_id', flat=True)
            qs = qs.exclude(id__in=answered_correct_ids)
            
        limit = self.request.query_params.get('limit', '20')
        if limit and limit.isdigit():
            qs = Question.objects.filter(id__in=list(qs.values_list('id', flat=True)[:int(limit)]))
            
        return qs.order_by('id')


class PracticeStartView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        topic_slug = request.data.get('topic_slug')
        difficulty = request.data.get('difficulty')
        count = int(request.data.get('count', 10))
        session_type = request.data.get('session_type', 'topic')

        user = request.user

        # Determine topic
        topic = None
        if topic_slug:
            topic = get_object_or_404(Topic, slug=topic_slug)

        from .engine import QuestionEngine

        if session_type == 'weak_area':
            # Drill weak areas
            questions_queryset = QuestionEngine.get_weak_area_questions(user, limit=count)
        else:
            # Build filters
            filters = {}
            if topic:
                filters['topic_id'] = topic.id
            if difficulty in ('easy', 'medium', 'hard'):
                filters['difficulty'] = difficulty

            questions_queryset = QuestionEngine.get_questions_for_user(user, filters, limit=count)

        questions_list = list(questions_queryset)
        if not questions_list:
            return Response({"error": "No questions found matching your criteria."}, status=404)

        session = PracticeSession.objects.create(
            user=user,
            session_type=session_type,
            topic=topic,
            difficulty=difficulty or '',
            total_questions=len(questions_list)
        )

        session_answers = [
            SessionAnswer(session=session, question=q)
            for q in questions_list
        ]
        SessionAnswer.objects.bulk_create(session_answers)

        serializer = QuestionSerializer(questions_list, many=True, context={'request': request})
        return Response({
            'session_id': session.id,
            'questions': serializer.data
        }, status=status.HTTP_201_CREATED)


class PracticeSubmitView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(PracticeSession, id=session_id, user=request.user)
        if session.completed_at:
            return Response({"error": "This session has already been completed."}, status=status.HTTP_400_BAD_REQUEST)
            
        answers_data = request.data.get('answers', [])
        total_time_secs = int(request.data.get('total_time_secs', 0))
        
        q_ids = [ans.get('question_id') for ans in answers_data if ans.get('question_id')]
        questions_map = {q.id: q for q in Question.objects.filter(id__in=q_ids)}
        
        correct_count = 0
        results_list = []
        
        for ans_item in answers_data:
            q_id = ans_item.get('question_id')
            selected = ans_item.get('selected_option', '')
            time_spent = int(ans_item.get('time_spent_secs', 0))
            
            question = questions_map.get(q_id)
            if not question:
                continue
                
            is_correct = (selected == question.correct_answer) if selected else False
            if is_correct:
                correct_count += 1
                
            SessionAnswer.objects.update_or_create(
                session=session,
                question=question,
                defaults={
                    'selected_option': selected,
                    'is_correct': is_correct,
                    'time_spent_secs': time_spent
                }
            )
            
            if selected:
                UserAnswer.objects.create(
                    user=request.user,
                    question=question,
                    selected_option=selected,
                    is_correct=is_correct
                )
                
            results_list.append({
                'question': QuestionResultSerializer(question, context={'request': request}).data,
                'selected_option': selected,
                'is_correct': is_correct
            })
            
        session.correct_count = correct_count
        session.total_questions = len(answers_data)
        session.time_taken_secs = total_time_secs
        session.completed_at = timezone.now()
        session.save()
        
        xp_earned = (correct_count * 10) + (len(answers_data) * 2)
        from questionbank.gamification import award_xp
        award_xp(request.user, xp_earned)
        
        return Response({
            'score_percent': session.score_percent,
            'correct_count': correct_count,
            'total_questions': len(answers_data),
            'xp_earned': xp_earned,
            'results': results_list
        }, status=200)


class WeakAreasView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        progress_records = TopicProgress.objects.filter(user=request.user).select_related('topic')
        weak_areas = []
        for tp in progress_records:
            if tp.is_weak_area:
                def calc(attempted, correct):
                    return round((correct / attempted) * 100, 1) if attempted > 0 else 0.0
                
                weak_areas.append({
                    'topic_name': tp.topic.name,
                    'topic_slug': tp.topic.slug,
                    'accuracy': tp.accuracy,
                    'total_attempted': tp.total_attempted,
                    'easy_accuracy': calc(tp.easy_attempted, tp.easy_correct),
                    'medium_accuracy': calc(tp.medium_attempted, tp.medium_correct),
                    'hard_accuracy': calc(tp.hard_attempted, tp.hard_correct),
                })
        return Response(weak_areas)


class TopicSummaryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        base_query = Q(institute__isnull=True)
        if hasattr(user, 'userprofile') and user.userprofile.institute:
            base_query |= Q(institute=user.userprofile.institute)
            
        preferred_exams = Exam.objects.none()
        if user and user.is_authenticated and hasattr(user, 'userprofile'):
            user_prefs = user.userprofile.preferred_exams.all()
            if user_prefs.exists():
                q_obj = Q()
                for exam in user_prefs:
                    q_obj |= Q(id=exam.id)
                    words = [w for w in exam.name.replace('(', '').replace(')', '').replace('/', ' ').split() if len(w) > 2]
                    if words:
                        sub_q = Q()
                        for word in words:
                            sub_q |= Q(name__icontains=word)
                        q_obj |= sub_q
                preferred_exams = Exam.objects.filter(q_obj).distinct()

        if preferred_exams.exists():
            syllabus_topics = Topic.objects.filter(examsyllabus__exam__in=preferred_exams).distinct()
            if syllabus_topics.exists():
                base_query &= Q(id__in=syllabus_topics)
                
        topics = Topic.objects.filter(base_query).distinct().order_by('name')
        progress_map = {
            tp.topic_id: tp for tp in TopicProgress.objects.filter(user=user)
        }
        
        summary = []
        for topic in topics:
            tp = progress_map.get(topic.id)
            
            def calc(attempted, correct):
                return round((correct / attempted) * 100, 1) if attempted > 0 else 0.0
                
            if tp:
                summary.append({
                    'topic_name': topic.name,
                    'topic_slug': topic.slug,
                    'accuracy': tp.accuracy,
                    'easy_accuracy': calc(tp.easy_attempted, tp.easy_correct),
                    'medium_accuracy': calc(tp.medium_attempted, tp.medium_correct),
                    'hard_accuracy': calc(tp.hard_attempted, tp.hard_correct),
                    'total_attempted': tp.total_attempted,
                    'last_practiced': tp.last_practiced
                })
            else:
                summary.append({
                    'topic_name': topic.name,
                    'topic_slug': topic.slug,
                    'accuracy': 0.0,
                    'easy_accuracy': 0.0,
                    'medium_accuracy': 0.0,
                    'hard_accuracy': 0.0,
                    'total_attempted': 0,
                    'last_practiced': None
                })
        return Response(summary)


# ===================================================================
# --- COMMUNITY QUESTION SUBMISSIONS ---
# ===================================================================

class SubmitQuestionView(generics.CreateAPIView):
    """Allows authenticated community users to submit new questions."""
    serializer_class = QuestionSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        response_serializer = UserSubmissionSerializer(question, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class MySubmissionsListView(generics.ListAPIView):
    """Lists submissions of the currently authenticated user."""
    serializer_class = UserSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Question.objects.filter(submitted_by=self.request.user).order_by('-id')


class PendingSubmissionsListView(generics.ListAPIView):
    """Lists pending submissions. Restricted to admins."""
    serializer_class = UserSubmissionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return Question.objects.filter(status='pending').order_by('-id')


class ApproveSubmissionView(views.APIView):
    """Approves a pending question, awarding XP to user."""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        if question.status == 'approved':
            return Response({'detail': 'Question is already approved.'}, status=status.HTTP_400_BAD_REQUEST)
        
        question.status = 'approved'
        question.verified = True
        question.is_verified = True
        question.save()

        # Award XP if submitted by a user
        if question.submitted_by:
            from questionbank.gamification import award_xp
            award_xp(question.submitted_by, 100)
            
            # Check if approved submissions >= 10
            approved_count = Question.objects.filter(
                submitted_by=question.submitted_by, 
                status='approved'
            ).count()
            
            if approved_count >= 10:
                profile = question.submitted_by.userprofile
                if not profile.is_content_creator:
                    profile.is_content_creator = True
                    profile.save(update_fields=['is_content_creator'])
                    
            logger.info(f"Notification: Question {question.id} approved. User {question.submitted_by.username} awarded 100 XP.")
        
        return Response({'detail': 'Question approved successfully.'}, status=status.HTTP_200_OK)


class RejectSubmissionView(views.APIView):
    """Rejects a pending question submission."""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        if question.status == 'rejected':
            return Response({'detail': 'Question is already rejected.'}, status=status.HTTP_400_BAD_REQUEST)
        
        question.status = 'rejected'
        question.save()
        
        if question.submitted_by:
            logger.info(f"Notification: Question {question.id} submitted by {question.submitted_by.username} was rejected.")
            
        return Response({'detail': 'Question rejected successfully.'}, status=status.HTTP_200_OK)


class UserActivityView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ans_dates = UserAnswer.objects.filter(user=request.user).values_list('answered_at__date', flat=True).distinct()
        feed_dates = UserFeedView.objects.filter(user=request.user).values_list('viewed_date', flat=True).distinct()
        
        all_dates = set()
        for d in ans_dates:
            if d:
                all_dates.add(d.strftime('%Y-%m-%d'))
        for d in feed_dates:
            if d:
                all_dates.add(d.strftime('%Y-%m-%d'))
                
        return Response({'activity': sorted(list(all_dates))})


class FriendsView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        profile = request.user.userprofile
        friends = profile.friends.all().select_related('user')
        friends_data = []
        for f in friends:
            friends_data.append({
                'username': f.user.username,
                'profile_photo': request.build_absolute_uri(f.profile_photo.url) if f.profile_photo else None,
                'district': f.district,
                'district_display': f.get_district_display() if f.district else '',
                'place': f.place,
                'xp': f.total_xp,
                'level': f.level,
                'streak': f.current_streak
            })
        return Response({'friends': friends_data})
        
    def post(self, request):
        username = request.data.get('username')
        if not username:
            return Response({'error': 'username is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if username == request.user.username:
            return Response({'error': 'You cannot add yourself as a friend.'}, status=status.HTTP_400_BAD_REQUEST)
            
        friend_user = get_object_or_404(User, username=username)
        profile = request.user.userprofile
        friend_profile = friend_user.userprofile
        
        profile.friends.add(friend_profile)
        
        return Response({
            'success': True,
            'message': f"Successfully added {username} as a friend."
        }, status=status.HTTP_200_OK)
        
    def delete(self, request):
        username = request.data.get('username') or request.query_params.get('username')
        if not username:
            return Response({'error': 'username is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        friend_user = get_object_or_404(User, username=username)
        profile = request.user.userprofile
        friend_profile = friend_user.userprofile
        
        profile.friends.remove(friend_profile)
        
        return Response({
            'success': True,
            'message': f"Successfully removed {username} as a friend."
        }, status=status.HTTP_200_OK)


class UserSearchView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'users': []})
            
        users = User.objects.filter(username__icontains=query).exclude(id=request.user.id)[:10]
        users_data = []
        profile = request.user.userprofile
        current_friends = profile.friends.all().values_list('user_id', flat=True)
        
        for u in users:
            prof, _ = UserProfile.objects.get_or_create(user=u)
            users_data.append({
                'username': u.username,
                'profile_photo': request.build_absolute_uri(prof.profile_photo.url) if prof.profile_photo else None,
                'district': prof.district,
                'district_display': prof.get_district_display() if prof.district else '',
                'is_friend': u.id in current_friends
            })
        return Response({'users': users_data})


