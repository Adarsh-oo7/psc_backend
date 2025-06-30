from django.urls import path
from . import views

urlpatterns = [
    # --- Auth and Profile URLs ---
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/user/', views.UserView.as_view(), name='user-detail'),
    path('auth/profile/', views.UserProfileView.as_view(), name='user-profile'),

    # --- Public Content URLs ---
    path('exams/', views.ExamListView.as_view(), name='exam-list'),
    path('topics/', views.TopicListView.as_view(), name='topic-list'),
    path('questions/', views.QuestionListView.as_view(), name='question-list'),
    path('questions/daily/', views.DailyQuestionView.as_view(), name='daily-question'),

    # --- NEW: URLs for the advanced Mock Exam mode ---
    path('generate-mock-exam/<int:exam_id>/', views.GenerateMockExamView.as_view(), name='generate-mock-exam'),
    path('submit-exam/', views.SubmitExamView.as_view(), name='submit-exam'),

    # --- User Action URLs ---
    path('submit-answer/', views.SubmitAnswerView.as_view(), name='submit-answer'),
    path('my-progress-dashboard/', views.MyProgressDashboardView.as_view(), name='my-progress-dashboard'),
    path('bookmarks/', views.BookmarkListCreateView.as_view(), name='bookmark-list-create'),
    path('reports/', views.ReportListCreateView.as_view(), name='report-list-create'),
    
    # --- Student-specific URLs ---
    path('my-messages/', views.MyMessagesListView.as_view(), name='my-messages-list'),
    path('messages/<int:pk>/mark-as-read/', views.MarkMessageAsReadView.as_view(), name='message-mark-read'),
    path('institute-join-request/', views.CreateJoinRequestView.as_view(), name='create-join-request'),
]