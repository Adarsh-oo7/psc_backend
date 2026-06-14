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
    path('students/add-by-username/', views.AddStudentByUsernameView.as_view(), name='institute-add-student-by-username'),
    path('students/<int:student_pk>/fees/', views.StudentFeeDashboardView.as_view(), name='student-fee-dashboard'),
    path('students/<int:student_pk>/record-payment/', views.StudentPaymentCreateView.as_view(), name='student-record-payment'),
    
    # Batches, Attendance, Notes
    path('batches/', views.BatchListCreateView.as_view(), name='batch-list'),
    path('batches/<int:pk>/', views.BatchDetailView.as_view(), name='batch-detail'),
    path('batches/<int:pk>/members/', views.BatchMembershipView.as_view(), name='batch-members'),
    path('batches/<int:pk>/attendance/', views.AttendanceListCreateView.as_view(), name='batch-attendance'),
    path('notes/', views.NoteListCreateView.as_view(), name='note-list'),
    path('notes/<int:pk>/', views.NoteDetailView.as_view(), name='note-detail'),

]