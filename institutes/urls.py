# institutes/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Endpoint for the institute to manage its own profile
    path('my-institute/', views.MyInstituteDetailView.as_view(), name='my-institute-detail'),
    
    # Endpoints for managing students
    path('students/', views.InstituteStudentListCreateView.as_view(), name='institute-student-list'),
    path('students/<int:pk>/', views.InstituteStudentDetailView.as_view(), name='institute-student-detail'),
    
    # Endpoints for managing custom topics
    path('topics/', views.InstituteTopicListCreateView.as_view(), name='institute-topic-list'),
    path('topics/<int:pk>/', views.InstituteTopicDetailView.as_view(), name='institute-topic-detail'),
    
    # Endpoints for managing custom questions
    path('questions/', views.InstituteQuestionListCreateView.as_view(), name='institute-question-list'),
    path('questions/<int:pk>/', views.InstituteQuestionDetailView.as_view(), name='institute-question-detail'),
    
    # Endpoint for sending messages
    path('messages/send/', views.InstituteMessageCreateView.as_view(), name='institute-send-message'),

    path('fees/<int:fee_pk>/payments/', views.FeePaymentCreateView.as_view(), name='fee-payment-create'),
    path('join-requests/', views.InstituteJoinRequestListView.as_view(), name='institute-join-requests'),
    path('join-requests/<int:request_id>/<str:action>/', views.ProcessJoinRequestView.as_view(), name='process-join-request'),
    path('public/list/', views.PublicInstituteListView.as_view(), name='public-institute-list'),
    path('public/detail/<slug:slug>/', views.PublicInstituteDetailView.as_view(), name='public-institute-detail'),
    path('public/portal/<slug:slug>/', views.PublicInstitutePortalView.as_view(), name='public-institute-portal'),
    path('public/submit-test/<slug:slug>/', views.PublicInstituteSubmitTestView.as_view(), name='public-institute-submit-test'),
    path('my-test-history/<slug:slug>/', views.StudentMyTestHistoryView.as_view(), name='student-my-test-history'),
    path('leaderboard/', views.InstituteLeaderboardView.as_view(), name='institute-leaderboard'),
    path('students/add-by-username/', views.AddStudentByUsernameView.as_view(), name='institute-add-student-by-username'),
    path('student/leave/', views.StudentLeaveInstituteView.as_view(), name='student-leave-institute'),
    path('students/<int:student_pk>/fees/', views.StudentFeeDashboardView.as_view(), name='student-fee-dashboard'),
    path('students/<int:student_pk>/results/', views.InstituteStudentResultsView.as_view(), name='student-results'),
    path('students/<int:student_pk>/record-payment/', views.StudentPaymentCreateView.as_view(), name='student-record-payment'),
    path('students/<int:pk>/phone/', views.InstituteUpdateStudentPhoneView.as_view(), name='institute-student-phone'),
    
    # Batches, Attendance, Notes
    path('batches/', views.BatchListCreateView.as_view(), name='batch-list'),
    path('batches/<int:pk>/', views.BatchDetailView.as_view(), name='batch-detail'),
    path('batches/<int:pk>/members/', views.BatchMembershipView.as_view(), name='batch-members'),
    path('batches/<int:pk>/attendance/', views.AttendanceListCreateView.as_view(), name='batch-attendance'),
    path('notes/', views.NoteListCreateView.as_view(), name='note-list'),
    path('notes/<int:pk>/', views.NoteDetailView.as_view(), name='note-detail'),

    # Mock Tests (Admin CRUD, scheduling, question assignment, and student exam taking)
    path('mock-tests/', views.InstituteMockTestListCreateView.as_view(), name='institute-mock-tests'),
    path('mock-tests/<int:pk>/', views.InstituteMockTestDetailView.as_view(), name='institute-mock-test-detail'),
    path('mock-tests/<int:pk>/submissions/', views.InstituteMockTestSubmissionsView.as_view(), name='institute-mock-test-submissions'),
    path('mock-tests/<int:pk>/add-question/', views.InstituteMockTestAddQuestionView.as_view(), name='institute-mock-test-add-question'),
    path('mock-tests/<int:pk>/manage-questions/', views.InstituteMockTestManageQuestionsView.as_view(), name='institute-mock-test-manage-questions'),
    path('public/mock-test/<slug:slug>/<int:test_id>/questions/', views.PublicInstituteMockTestQuestionsView.as_view(), name='public-institute-mock-test-questions'),
]