# --- Imports ---
from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Case, When, FloatField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from random import choice, shuffle
import logging

# Local application imports
from .models import (
    Exam, Topic, Question, Bookmark, Report, UserProfile, 
    UserAnswer, ExamCategory, ExamSyllabus
)
from .serializers import (
    ExamSerializer, TopicSerializer, QuestionSerializer,
    BookmarkSerializer, ReportSerializer, UserSerializer, 
    UserProfileSerializer, UserAnswerSerializer, ExamCategorySerializer
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
        return Topic.objects.filter(base_query).distinct().order_by('name')

# In questionbank/views.py

class QuestionListView(generics.ListAPIView):
    """
    Lists questions available to the user.
    - Can be filtered by `exam_id` or `topic_id`.
    - Can be limited to a random subset using the `limit` parameter for Quiz Mode.
    """
    serializer_class = QuestionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user = self.request.user
        
        # Start with a base of questions that are "Global" (have no institute)
        base_query = Q(institute__isnull=True)

        # If the user is logged in and belongs to an institute, also include that institute's private questions
        if user.is_authenticated and hasattr(user, 'userprofile') and user.userprofile.institute:
            base_query |= Q(institute=user.userprofile.institute)
        
        allowed_questions = Question.objects.filter(base_query)
        
        # Apply filters from the URL query parameters
        exam_id = self.request.query_params.get('exam_id')
        if exam_id:
            # Correctly filter across the 'exams' many-to-many relationship
            allowed_questions = allowed_questions.filter(exams__id=exam_id)
        
        topic_id = self.request.query_params.get('topic_id')
        if topic_id:
            allowed_questions = allowed_questions.filter(topic_id=topic_id)
        
        # This is the logic that enables both Study Mode and Quiz Mode
        limit = self.request.query_params.get('limit')
        if limit and limit.isdigit():
            # For Quiz Mode: order randomly and take the specified number of questions
            return allowed_questions.order_by('?')[:int(limit)]
            
        # For Study Mode (no limit specified): return all matching questions
        return allowed_questions.distinct()
    
    

class DailyQuestionView(views.APIView):
    """Provides a single random question for a daily quiz."""
    permission_classes = [AllowAny]
    def get(self, request):
        user = request.user
        base_query = Q(institute__isnull=True)
        if user.is_authenticated and hasattr(user, 'userprofile') and user.userprofile.institute:
            base_query |= Q(institute=user.userprofile.institute)
        questions_pool = Question.objects.filter(base_query)
        if not questions_pool.exists():
            return Response({'error': 'No questions available'}, status=status.HTTP_404_NOT_FOUND)
        question = choice(list(questions_pool))
        return Response(QuestionSerializer(question).data)


# ===================================================================
# --- MOCK EXAM & PROGRESS VIEWS ---
# ===================================================================

class GenerateMockExamView(views.APIView):
    """Generates a full mock exam based on the ExamSyllabus."""
    permission_classes = [IsAuthenticated]
    def get(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
        syllabus_parts = exam.syllabus_parts.all()
        all_questions = []
        for part in syllabus_parts:
            # Get random questions for each topic as defined in the syllabus
            questions = list(Question.objects.filter(topic=part.topic).order_by('?')[:part.num_questions])
            all_questions.extend(questions)
        shuffle(all_questions)
        response_data = {
            'exam_name': exam.name, 'duration_minutes': exam.duration_minutes,
            'questions': QuestionSerializer(all_questions, many=True).data
        }
        return Response(response_data)

class SubmitAnswerView(generics.CreateAPIView):
    """Saves a user's single answer during a simple practice quiz."""
    serializer_class = UserAnswerSerializer
    permission_classes = [IsAuthenticated]
    def perform_create(self, serializer):
        question = serializer.validated_data['question']
        selected_option = serializer.validated_data['selected_option']
        is_correct = (selected_option == question.correct_answer)
        serializer.save(user=self.request.user, is_correct=is_correct)


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

        response_data = {
            'results': {
                'score': round(final_score, 2),
                'total': len(all_question_ids),
                'correct': correct_count,
                'wrong': wrong_count,
                'unanswered': unanswered_count,
            },
            'questions': QuestionSerializer(questions, many=True).data
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
                return Response({"message": "Please set one or more focus exams in your profile to see a personalized report."})
            
            report_title = f"Focus Report: {', '.join([exam.name for exam in focus_exams])}"
            # Filter answers to only include questions from the user's focus exams
            answers_to_process = all_answers.filter(question__exams__in=focus_exams)
        
        if not answers_to_process.exists():
            return Response({"message": f"No progress data available yet for '{report_title}'. Start taking quizzes!"})
            
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

        # --- 3. Calculate Overall Stats ---
        total_answered = answers_to_process.count()
        correct_count = answers_to_process.filter(is_correct=True).count()
        wrong_count = total_answered - correct_count
        net_marks = (correct_count * 1) - (wrong_count * 0.33)
        accuracy = (correct_count * 100.0 / total_answered) if total_answered > 0 else 0
        
        # --- 4. Get Recent Answer History ---
        recent_answers = answers_to_process.order_by('-answered_at')[:50]

        # --- 5. Assemble the final data object for the API response ---
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
            'answer_history': DetailedUserAnswerSerializer(recent_answers, many=True).data
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
from .models import DailyExam, Questions
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
# views.py
# views.py
from .models import Questions

class BulkUploadView:
    def process_questions_text(self, text_data):
        created_questions = []
        errors = []
        lines = text_data.strip().split('\n')

        for line in lines:
            try:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) < 6:
                    errors.append(f"Incomplete line: {line}")
                    continue

                q = Questions.objects.create(
                    question_text=parts[0],
                    option_a=parts[1],
                    option_b=parts[2],
                    option_c=parts[3],
                    option_d=parts[4],
                    correct_answer=parts[5].upper(),
                    explanation=parts[6] if len(parts) > 6 else ''
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
            return Response({
                'score': score, 'correct_count': correct_count, 'total_questions': questions.count()
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
        return ModelExam.objects.filter(exam_id=exam_id)

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
            
            return Response({
                'score': score, 
                'correct_count': correct_count, 
                'total_questions': total_questions,
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
        return PreviousYearPaper.objects.filter(exam_id=exam_id)



# In questionbank/views.py
from .models import Syllabus, ExamAnnouncement
from .serializers import SyllabusSerializer, ExamAnnouncementSerializer
from django.utils import timezone   


class ExamSyllabusListView(generics.ListAPIView):
    queryset = Syllabus.objects.all()
    serializer_class = SyllabusSerializer
    permission_classes = [AllowAny]


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
