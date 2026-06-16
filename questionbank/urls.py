from django.urls import path
from . import views

urlpatterns = [
    # --- Auth and Profile URLs ---
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/user/', views.UserView.as_view(), name='user-detail'),
    path('auth/profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('auth/google/', views.GoogleSignInView.as_view(), name='google-login'),
    path('auth/profile/activity/', views.UserActivityView.as_view(), name='user-activity'),
    path('friends/', views.FriendsView.as_view(), name='friends-list-create'),
    path('users/search/', views.UserSearchView.as_view(), name='users-search'),

    # --- Public Content URLs ---
    path('exams/', views.ExamListView.as_view(), name='exam-list'),
    path('topics/', views.TopicListView.as_view(), name='topic-list'),
    path('questions/', views.QuestionListView.as_view(), name='question-list'),
    path('questions/daily/', views.DailyQuestionView.as_view(), name='daily-question'),
    path('questions/daily-quiz/', views.DailyQuizView.as_view(), name='daily-quiz'),
    path('questions/weak-areas/', views.WeakAreaQuestionsView.as_view(), name='weak-area-questions'),
    path('questions/submit/', views.SubmitQuestionView.as_view(), name='submit-question'),
    path('questions/my-submissions/', views.MySubmissionsListView.as_view(), name='my-submissions'),
    path('questions/pending/', views.PendingSubmissionsListView.as_view(), name='pending-submissions'),
    path('questions/<int:pk>/approve/', views.ApproveSubmissionView.as_view(), name='approve-submission'),
    path('questions/<int:pk>/reject/', views.RejectSubmissionView.as_view(), name='reject-submission'),
    
    # --- Public SEO URLs ---
    path('public/questions/<slug:slug>/', views.PublicQuestionDetailView.as_view(), name='public-question-detail'),
    path('public/topics/<slug:slug>/', views.PublicTopicDetailView.as_view(), name='public-topic-detail'),
    path('public/exams/<slug:slug>/', views.PublicExamDetailView.as_view(), name='public-exam-detail'),
    path('public/current-affairs/', views.PublicCurrentAffairsListView.as_view(), name='public-current-affairs-list'),
    path('public/current-affairs/<slug:slug>/', views.PublicCurrentAffairsDetailView.as_view(), name='public-current-affairs-detail'),

    # --- NEW: URLs for the advanced Mock Exam mode ---
    path('generate-mock-exam/<int:exam_id>/', views.GenerateMockExamView.as_view(), name='generate-mock-exam'),
    path('submit-exam/', views.SubmitExamView.as_view(), name='submit-exam'),

    # --- User Action URLs ---
    path('submit-answer/', views.SubmitAnswerView.as_view(), name='submit-answer'),
    path('my-progress-dashboard/', views.MyProgressDashboardView.as_view(), name='my-progress-dashboard'),
    path('bookmarks/', views.BookmarkListCreateView.as_view(), name='bookmark-list-create'),
    path('reports/', views.ReportListCreateView.as_view(), name='report-list-create'),
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
    path('wrong-answers/', views.WrongAnswersView.as_view(), name='wrong-answers'),
    path('goals/', views.WeeklyGoalsView.as_view(), name='weekly-goals'),
    
    # --- Student-specific URLs ---
    path('my-messages/', views.MyMessagesListView.as_view(), name='my-messages-list'),
    path('messages/<int:pk>/mark-as-read/', views.MarkMessageAsReadView.as_view(), name='message-mark-read'),
    path('institute-join-request/', views.CreateJoinRequestView.as_view(), name='create-join-request'),



    path('daily-exams/', views.DailyExamListView.as_view(), name='daily-exam-list'),
    path('daily-exams/<int:pk>/submit/', views.SubmitDailyExamView.as_view(), name='submit-daily-exam'),
    path('daily-exams/<int:pk>/leaderboard/', views.DailyExamLeaderboardView.as_view(), name='daily-exam-leaderboard'),

    # path('bulk-upload/',views.BulkUploadView.as_view(), name='bulk_upload'),
    # path('text-upload/', views.TextUploadView.as_view(), name='text_upload'),



    # --- Model Exam URLs ---URLs ...
    path('exams/<int:exam_id>/model-exams/', views.ModelExamListView.as_view(), name='model-exam-list'),
    path('model-exams/<int:pk>/', views.ModelExamDetailView.as_view(), name='model-exam-detail'),
    path('model-exams/<int:pk>/submit/', views.SubmitModelExamView.as_view(), name='submit-model-exam'),


    path('exams/<int:exam_id>/pyq/', views.PYQListView.as_view(), name='pyq-list'),


    path('exam-calendar/', views.ExamCalendarView.as_view(), name='exam-calendar'),



    path('syllabuses/', views.ExamSyllabusListView.as_view(), name='syllabus-list'),
    path('profiles/<str:username>/', views.PublicUserProfileView.as_view(), name='public-user-profile'),

    # --- Gamification and Study Feed Routes ---
    path('study-feed/', views.StudyFeedView.as_view(), name='study-feed'),
    path('study-feed/view/', views.RecordCardView.as_view(), name='study-feed-view'),
    path('questions/<int:pk>/explanation/', views.QuestionExplanationView.as_view(), name='question-explanation'),

    # --- Study Flow & Analytics URLs ---
    path('topics/', views.TopicListView.as_view(), name='topic-list'),
    path('topics/<slug:slug>/questions/', views.TopicQuestionsView.as_view(), name='topic-questions'),
    path('practice/start/', views.PracticeStartView.as_view(), name='practice-start'),
    path('practice/<int:session_id>/submit/', views.PracticeSubmitView.as_view(), name='practice-submit'),
    path('analytics/weak-areas/', views.WeakAreasView.as_view(), name='weak-areas'),
    path('analytics/topic-summary/', views.TopicSummaryView.as_view(), name='topic-summary'),
]